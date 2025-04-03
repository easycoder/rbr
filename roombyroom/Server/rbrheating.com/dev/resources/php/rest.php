<?php
    // REST server

    // This small REST server gives you the ability to manage tables
    // in your site database.
    use PHPMailer\PHPMailer\PHPMailer;
    use PHPMailer\PHPMailer\Exception;

    require '/home/rbrheating/PHPMailer/src/Exception.php';
    require '/home/rbrheating/PHPMailer/src/PHPMailer.php';
    require '/home/rbrheating/PHPMailer/src/SMTP.php';

    require_once "statistics.php";

    date_default_timezone_set('Europe/London');
//      logger(substr($_SERVER['PATH_INFO'], 1));
    $request = explode("/", substr($_SERVER['PATH_INFO'], 1));
    $action = array_shift($request);
    $method = $_SERVER['REQUEST_METHOD'];
    chdir("../..");
    $cwd = getcwd();

    $props = array();
    $filename = '../../' . $_SERVER['HTTP_HOST'] . '.txt';
//     logger($filename);
    if (file_exists($filename)) {
        $file = fopen($filename, 'r');
        while (!feof($file)) {
            $ss = trim(fgets($file));
            if (!$ss || substr($ss, 0, 1) == '#') {
                continue;
            }
            $ss = explode('=', $ss, 2);
            if (count($ss) > 1) {
                $props[$ss[0]] = $ss[1];
            }
        }
        fclose($file);
    } else {
         logger("Properties file $filename not found");
         print("Properties file $filename not found");
         exit;
    }

    // First, the commands that don't require a database table name.
    switch ($method) {
        case 'GET':
            switch ($action) {
                case '_list':
                    // List the contents of a directory
                    // Endpoint: {site root}/resources/php/rest.php/_list/[{path}]
//                  Start at the resources folder
                    $path = $cwd . '/resources/';
                    if (count($request)) {
                         $path .= str_replace('~', '/', $request[0]);
                    }
                    $files = scandir($path);
                    print '[';
                    // First list all the directories
                    $flag = false;
                    foreach ($files as $file) {
                        if (strpos($file, '.') !== 0) {
                            if (is_dir("$path/$file")) {
                                if ($flag) {
                                    print ',';
                                } else {
                                    $flag = true;
                                }
                                print "{\"name\":\"$file\",\"type\":\"dir\"}";
                            }
                        }
                    }
                    // Now do the ordinary files
                    foreach ($files as $file) {
                        if (strpos($file, '.') !== 0) {
                            if (!is_dir("$path/$file")) {
                                if ($flag) {
                                    print ',';
                                } else {
                                    $flag = true;
                                }
                                $type = 'file';
                                $p = strrpos($file, '.');
                                if ($p > 0) {
                                    $ext = substr($file, $p + 1);
                                    $type = $ext;
                                    switch (strtolower($ext)) {
                                        case 'jpg':
                                        case 'png':
                                        case 'gif':
                                            $type = 'img';
                                            break;
                                    }
                                }
                                print "{\"name\":\"$file\",\"type\":\"$type\"}";
                            }
                        }
                    }
                    print ']';
                    exit;
                case '_hash':
                    // Get a hash of a value
                    // Endpoint: {site root}/easycoder/rest.php/_hash/{value-to-hash}
                    print password_hash($request[0], PASSWORD_DEFAULT);
                    exit;
                case '_verify':
                    // Verify a hash
                    // Endpoint: {site root}/easycoder/rest.php/_verify/{value-to-verify}
                    print password_verify($request[0], $props['password']) ? 'yes' : 'no';
                    exit;
                case '_exists':
                    // Test if a file exists
                    // Endpoint: {site root}/easycoder/rest.php/_exists/{path}
                    $path = $cwd . '/resources/' . str_replace('~', '/', $request[0]);
                    print file_exists($path) ? 'Y' : '';
                    exit;
                case '_test':
                    // Endpoint: {site root}/easycoder/rest.php/_test/
                    print_r($_SERVER[SERVER_NAME]);
                    exit;
            }
            break;
        case 'POST':
            // These endpoints require the admin password
            if ($action[0] == '_') {
                switch ($action) {
                    case '_mkdir':
                        // Create a directory
                        // Endpoint: {site root}/easycoder/rest.php/_mkdir
                        header("Content-Type: application/text");
                        $path = stripslashes(file_get_contents("php://input"));
                         logger("Create directory $path");
                        mkdir($path);
                        exit;
                    case '_save':
                        // Save data to a file in the resources folder
                        // Endpoint: {site root}/easycoder/rest.php/_save/{path}
                        $path = $cwd . '/resources/' . str_replace('~', '/', $request[0]);
                        $p = strrpos($path, '/');
                        $dir = substr($path, 0, $p);
                        mkdir($dir, 0777, true);
                        header("Content-Type: application/text");
                        $content = base64_decode(stripslashes(file_get_contents("php://input")));
                        $p = strrpos($path, '.');
                        $root = substr($path, 0, $p);
                        $ext = substr($path, $p);
                        file_put_contents($path, $content);
                        exit;
                    case '_delete':
                        // Delete a file in the resources folder
                        // Endpoint: {site root}/easycoder/rest.php/_delete/{path}
                        $path = $cwd . '/resources/' . str_replace('~', '/', $request[0]);
                        if (is_dir($path)) {
                            rmdir($path);
                        } else {
                            unlink($path);
                        }
                        exit;
                    default:
                        http_response_code(404);
                        print "I don't understand this admin request.";
                        break;
                }
            break;
        }
    }

    // The remaining commands require use of the database.
    $smtpusername = $props['smtpusername'];
    $smtppassword = $props['smtppassword'];
    $conn = mysqli_connect($props['sqlhost'], $props['sqluser'],
    $props['sqlpassword'], $props['sqldatabase']);
    if (!$conn)
    {
        http_response_code(404);
        die("Failed to connect to MySQL: " . mysqli_connect_error());
    }
    mysqli_set_charset($conn, 'utf8');

    if (!count($request)) {
        http_response_code(400);
        print "{\"message\":\"Incomplete REST query: ".substr($_SERVER['PATH_INFO'], 1).".\"}";
        exit;
    }

     switch ($method) {

        case 'GET':
            get($conn, $action, $request, $smtpusername, $smtppassword);
            break;

        case 'POST':
            post($conn, $action, $request, $smtpusername, $smtppassword);
            break;

        default:
            http_response_code(400);
            break;
    }
    mysqli_close($conn);
    exit;

    // GET
    function get($conn, $action, $request, $smtpusername, $smtppassword) {
        $ts = time();
        switch ($action) {

            // Endpoints called by the system controller

            case 'register':
                // Register a new MAC and get the password.
                // Endpoint: {site root}/resources/php/rest.php/register/<mac>
                $mac = trim($request[0]);
                if ($mac) {
                    $result = query($conn, "SELECT password FROM systems WHERE mac='$mac'");
                    if ($row = mysqli_fetch_object($result)) {
                        $password = $row->password;
                    } else {
                        $password = rand(100000, 999999);
                        $map = '{"profiles":[{"name":"Unnamed","rooms":[{"name":"Unnamed","sensor":"","relays":[""],"mode":"off","target":"0.0","events":[]}],"message":"OK"}],"profile":0,"name":"New system"}';
                        $map = base64_encode($map);
                        query($conn, "INSERT INTO systems (ts,mac,password,map) VALUES ('$ts','$mac','$password','$map')");
                        logger("INSERT INTO systems (ts,mac,password) VALUES ('$ts','$mac','$password')");
                    }
                    $file = fopen('version', 'r');
                    $version = trim(fgets($file));
                    fclose($file);
                    print '{"password":"'.$password.'","version":"'.$version.'"}';
                }
                break;

            case 'config':
                // Get the system config file, given its MAC.
                // Endpoint: {site root}/resources/php/rest.php/config/<mac>
                $mac = $request[0];
                $result = query($conn, "SELECT config FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    print base64_decode($row->config);
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            case 'map':
                // Get the system map, given its MAC.
                // Endpoint: {site root}/resources/php/rest.php/map/<mac>
                $mac = $request[0];
                $result = query($conn, "SELECT map FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = base64_decode($row->map);
                    $map = str_replace('!_SP_!', ' ', $map);
                    print $map;
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            case 'request':
                // Get the current request.
                // Endpoint: {site root}/resources/php/rest.php/request/<mac>
                $mac = $request[0];
                $result = query($conn, "SELECT request FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $value = $row->request;
                    if ($value) {
                        $value = base64_decode($value);
                        print $value;
                        // query($conn, "UPDATE systems SET request='' WHERE mac='$mac'");
                        // logger("UPDATE systems SET request='' WHERE mac='$mac'");
                    }
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            case 'confirm':
                // Get the confirmation. Requested by UI.
                // Endpoint: {site root}/resources/php/rest.php/confirm/<mac>
                $mac = $request[0];
                $result = query($conn, "SELECT confirm FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    print $row->confirm;
                    query($conn, "UPDATE systems SET confirm='' WHERE mac='$mac'");
                    logger("UPDATE systems SET confirm='' WHERE mac='$mac'");
                }
                mysqli_free_result($result);
                break;

            // Endpoints called by the user.

            case 'user':
                // Get the confirmation. Requested by UI.
                // Endpoint: {site root}/resources/php/rest.php/user/<email>
                $email = $request[0];
                $password = '';
                if (count($request) > 1) {
                    $password = $request[1];
                }
                // Look for the user record
                $result = query($conn, "SELECT password FROM users WHERE email='$email'");
                if ($row = mysqli_fetch_object($result)) {
                    //Record found, so check the password
                    if ($row->password == $password) {
                        print "{\"message\": \"found\"}";
                    }
                    else {
                        print "{\"message\": \"badpassword\"}";
                    }
                } else {
                    //No user record, so create one
                    $timestamp = time();
                    $password = rand(100000, 999999);
                    $message = "Welcome to RBR Heating. Your user name is <b>$email</b> "
                        ."and your password is <b>$password</b>.<br><br>"
                        . "<a href=\"https://rbrheating.com/home/resources/php/rest.php/confirmuser/$email/$password\"> "
                        . "Click/tap here to confirm these values</a><br><br>"
                        . "(If you did not request to register with RBR Heating, please ignore this email.)";
                    $data = new stdClass();
                    $data->email = $email;
                    $data->subject = "RBR Heating - new user";
                    $data->message = $message;
                    $data->smtpusername = $smtpusername;
                    $data->smtppassword = $smtppassword;
                    try {
                        sendMail($data);
                        $xpassword = "x$password";
                        query($conn, "INSERT INTO users (email, password) VALUES ('$email','$xpassword')");
                        logger("INSERT INTO user (email, password) VALUES ('$email','$xpassword')");
                        print "{\"message\": \"$xpassword\"}";
                    } catch (Exception $e) {
                        http_response_code(404);
                        print "{\"message\": $data->err}";
                        break;
                    }
                }
                mysqli_free_result($result);
                break;

            case 'confirmuser':
                // Confirm the user. Requested by a link in an email.
                // Endpoint: {site root}/resources/php/rest.php/confirmuser/<email>/<password>
                $email = $request[0];
                $password = $request[1];
                $xpassword = "$password";
                $result = query($conn, "SELECT null FROM users WHERE email='$email' AND password='$password'");
                logger("SELECT null FROM user WHERE email='$email' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $message = "You are now registered with RBR Heating with the following credentials:<br><br>"
                        . "User name: $email<br>"
                        . "Password: $password<br><br>"
                        . "Please save these details. You should only need them if you change to a different browser "
                        . "or use a different device to access RBR Heating.";
                    $data = new stdClass();
                    $data->sender = "RBR Heating Admin";
                    $data->email = $email;
                    $data->subject = "RBR Heating - user confirmed";
                    $data->message = $message;
                    $data->smtpusername = $smtpusername;
                    $data->smtppassword = $smtppassword;
                    try {
                        sendMail($data);
                        query($conn, "UPDATE users SET password='$password' WHERE email='$email'");
                        logger("UPDATE users SET password='$password' WHERE email='$email'");
                    } catch (Exception $e) {
                        http_response_code(404);
                        print "{\"message\": $data->err}";
                        break;
                    }
                    print "You are now registered with RBR Heating with the following credentials:<br><br>"
                        . "User name: $email<br>"
                        . "Password: $password<br><br>"
                        . "Please save these details. You should only need them if you change to a different browser "
                        . "or use a different device to access RBR Heating.";
                } else {
                    print "No record found";
                    http_response_code(404);
                }
                mysqli_free_result($result);
                break;

            case 'managed':
                // Get the systems managed by this user
                // Endpoint: {site root}/resources/php/rest.php/managed/<email>/<password>
                $email = $request[0];
                $password = $request[1];
                $result = query($conn, "SELECT systems FROM users WHERE email='$email' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    print base64_decode($row->systems);
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            case 'logdata':
                // Get log values for a given MAC and a range of times
                // Endpoint: {site root}/resources/php/rest.php/sensors/<mac>/ts1/ts2
                $mac = $request[0];
                $ts1 = $request[1];
                $ts2 = $request[2];
                print $mac;
                $result = query($conn, "SELECT sensors FROM sensors WHERE mac='$mac' AND ts>=$ts1 AND ts<$ts2");
                while ($row = mysqli_fetch_object($result)) {
                    $sensors = base64_decode($row->sensors);
                    print "$sensors\n";
                }
                mysqli_free_result($result);
                break;

            case 'requests':
                // Get a requests, given the MAC
                // Endpoint: {site root}/resources/php/rest.php/requests/<mac>/<count>
                $mac = $request[0];
                // $count = $request[1] * 2;
                // $result = query($conn, "SELECT * FROM (SELECT * FROM requests WHERE mac='$mac' ORDER BY ts DESC LIMIT $count) AS sub ORDER BY ts ASC");
                $result = query($conn, "SELECT * FROM requests WHERE mac='$mac' ORDER BY ts ASC");
                $data = array();
                while ($row = mysqli_fetch_object($result)) {
                    $item = new stdClass();
                    $item->ts = $row->ts;
                    $item->request = base64_decode($row->request);
                    $data[] = $item;
                }
                print json_encode($data);
                mysqli_free_result($result);
                break;

            case 'sensors':
                // Get the systems sensor values, given its MAC
                // Endpoint: {site root}/resources/php/rest.php/sensors/<mac>
                $mac = $request[0];
                $result = query($conn, "SELECT sensors FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $sensors = base64_decode($row->sensors);
                    print $sensors;
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            case 'sensorlog':
                // Get a system's sensor log, given its MAC
                // Endpoint: {site root}/resources/php/rest.php/sensorlog/<mac>/<password>
                $mac = $request[0];
                $password = $request[1];
                $result = query($conn, "SELECT map FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = base64_decode($row->map);
                    $map = str_replace('!_SP_!', ' ', $map);
                    $map = json_decode($map);
                    $name = str_replace('%20', ' ', $map->name);
                    mysqli_free_result($result);

                    // Read all the sensor logs for this system up to the start of the current month
                    $year = date("Y");
                    $month = date("m");
                    $date = new DateTime();
                    $date->setDate($year, $month, 1);
                    $date->setTime(0, 0);
                    $ts = $date->getTimestamp();

                    $stats = "";
                    $result = query($conn, "SELECT sensors FROM sensors WHERE mac='$mac' AND ts<$ts ORDER BY ts");
                    while ($row = mysqli_fetch_object($result)) {
                        $sensors = base64_decode($row->sensors);
                        if ($stats) $stats = "$stats<br>";
                        $stats = "$stats$sensors";
                    }
                    mysqli_free_result($result);
                    // print $stats;
                    $delay = mt_rand(1, 60);
                    print "Wait $delay seconds\n";
                    usleep($delay);

                    // Use the 'managed' table to find the user email, then send the stats.
                    $result = query($conn, "SELECT email FROM managed WHERE mac='$mac'");
                    while ($row = mysqli_fetch_object($result)) {
                        $email = $row->email;
                        $result2 = query($conn, "SELECT password FROM users WHERE email='$email'");
                        if ($row = mysqli_fetch_object($result2)) {
                            $date = date("Y/m", $ts - 24*60*60);
                            $password = $row->password;
                            $data = new stdClass();
                            $data->sender = "RBR statistics";
                            $data->email = $email;
                            $data->subject = "RBR Heating for $date at $name";
                            $data->message = $stats;
                            $data->smtpusername = $smtpusername;
                            $data->smtppassword = $smtppassword;
                            try {
                                sendMail($data);
                                print "Email sent to $email\n";
                            } catch (Exception $e) {
                                http_response_code(404);
                                print "{\"message\": $data->err}";
                                break;
                            }
                        }
                        mysqli_free_result($result2);
                    }
                    mysqli_free_result($result);
                    $result = query($conn, "Delete FROM sensors WHERE mac='$mac' AND ts<$ts");
                } else {
                    http_response_code(404);
                    print "MAC '$mac' and password '$password' do not match any record.";
                }
                break;

            case 'stats':
                // Endpoint: {site root}/resources/php/rest.php/stats/{mac}/{action}/...}
                doStatistics($conn, $request);
                break;

            case 'psu':
                // Get the psu request, if any.
                // Endpoint: {site root}/resources/php/rest.php/psu/<mac>/{password}
                $mac = trim($request[0]);
                if ($mac == "v") {
                    $file = fopen('psu/version', 'r');
                    $version = trim(fgets($file));
                    fclose($file);
                    print $version;
                } else if ($mac == "d") {
                    print file_get_contents("psu/download");
                } else {
                    $password = trim($request[1]);
                    $result = query($conn, "SELECT psu FROM systems WHERE mac='$mac' AND password='$password'");
                    if ($row = mysqli_fetch_object($result)) {
                        query($conn, "UPDATE systems SET psu='' WHERE mac='$mac'");
                        print $row->psu;
                    } else {
                        http_response_code(404);
                        print "MAC '$mac' and password '$password' do not match any record.";
                    }
                }
                break;

                // Test endpoints

            case 'test':
                // A test endpoint
                // Endpoint: {site root}/resources/php/rest.php/test/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    print "Test passed\n";
                    $year = date("Y");
                    $month = date("m");
                    print "$year - $month\n";
                    $date = new DateTime();
                    $date->setDate($year, $month, 1);
                    $date->setTime(0, 0);
                    $ts = $date->getTimestamp();
                    print "$ts\n";
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC $mac and password $password do not match any record.\"}";
                }
                break;

            case 'testread':
                // A test endpoint that reads from the 'test' field
                // Endpoint: {site root}/resources/php/rest.php/testread/{mac}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT test FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $test = $row->test;
                    print $test;
                } else {
                    http_response_code(404);
                    print "System with MAC '$mac' not found.";
                }
                break;

            case 'testwrite':
                // A test endpoint that writes to the 'test' field
                // Endpoint: {site root}/resources/php/rest.php/testwrite/{mac}/{password}/{message}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $message = trim($request[2]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    query($conn, "UPDATE systems SET test='$message' WHERE mac='$mac'");
                    print $message;
                } else {
                    http_response_code(404);
                    print "MAC '$mac' and password '$password' do not match any record.";
                }
                break;

            case 'roomname':
                // A test endpoint that returns a value
                // Endpoint: {site root}/resources/php/rest.php/test/{mac}/{password}/{roomindex}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $roomindex = intval(trim($request[2]));
                $result = query($conn, "SELECT map FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = $row->map;
                    $map = base64_decode($map);
                    $map = json_decode($map);
                    $room = $map->rooms[$roomindex];
                    $name = $room->name;
                    print "Room: $name";
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC $mac and password $password do not match any record.\"}";
                }
                break;

            default:
                http_response_code(404);
                print "I don't understand this request.";
                break;
         }
    }

    /////////////////////////////////////////////////////////////////////////
    // POST
    function post($conn, $action, $request, $smtpusername, $smtppassword) {
        $ts = time();
        switch ($action) {

            case 'config':
                // Save the system config file
                // Endpoint: {site root}/resources/php/rest.php/config/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $config = file_get_contents("php://input");
                    $config = base64_encode($config);
//                    print "$config\n";
                    query($conn, "UPDATE systems SET config='$config', last=$ts WHERE mac='$mac'");
                    logger("UPDATE systems SET config='$config' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'map':
                // Save the system map
                // Endpoint: {site root}/resources/php/rest.php/map/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = file_get_contents("php://input");
                    $map = str_replace(' ', '!_SP_!', $map);
                    $map = base64_encode($map);
//                    print "$map\n";
                    query($conn, "UPDATE systems SET map='$map', last=$ts WHERE mac='$mac'");
                    logger("UPDATE systems SET map='$map' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'confirm':
                // Save the system map and confirm a request
                // Endpoint: {site root}/resources/php/rest.php/map/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = file_get_contents("php://input");
                    $map = base64_encode($map);
                    query($conn, "UPDATE systems SET map='$map', request='', confirm='Y', last=$ts WHERE mac='$mac'");
                    logger("UPDATE systems SET map='$map', request='', confirm='Y', last=$ts WHERE mac='$mac'");
                    // Write to the requests log
                    $data = base64_encode('{}');
                    query($conn, "INSERT INTO requests (ts, mac,request) VALUES ('$ts','$mac','$data')");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'request':
                // Handle a request sent by the UI
                // Endpoint: {site root}/resources/php/rest.php/request/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password=$password");
                if ($row = mysqli_fetch_object($result)) {
                    $data = file_get_contents("php://input");
                    logger($data);
                    $data = base64_encode($data);
                    print("UPDATE systems SET request='$data', confirm='', last=$ts WHERE mac='$mac'\n");
                    query($conn, "UPDATE systems SET request='$data', confirm='', last=$ts WHERE mac='$mac'");
                    logger("UPDATE systems SET request='$data', last=$ts WHERE mac='$mac'");
                    // Write to the requests log
                    query($conn, "INSERT INTO requests (ts, mac,request) VALUES ('$ts','$mac','$data')");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'sensorlog':
                // Record a set of sensor data.
                // Endpoint: {site root}/resources/php/rest.php/sensorlog/<mac>/<password>
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password=$password");
                if ($row = mysqli_fetch_object($result)) {
                    $sensors = file_get_contents("php://input");
                    $encoded = base64_encode($sensors);
                    query($conn, "INSERT INTO sensors (ts,mac,sensors) VALUES ('$ts','$mac','$encoded')");
                    logger("INSERT INTO sensors (ts,mac,sensors) VALUES ('$ts','$mac','$encoded')");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'sensors':
                // Update sensor values. This clears the request. It also records statistics.
                // Endpoint: {site root}/resources/php/rest.php/sensors/<mac>/<password>
                $mac = $request[0];
                $password = $request[1];
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $sensors = file_get_contents("php://input");
                    $encoded = base64_encode($sensors);
                    query($conn, "UPDATE systems SET sensors='$encoded' WHERE mac='$mac'");
                    logger("UPDATE systems SET sensors='$encoded' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                    break;
                }
                break;

            case 'advance':
                // Clear an 'advance' request (sent by controller)
                // Endpoint: {site root}/resources/php/rest.php/advance/{mac}/{password}/{profile}/{roomindex}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $currentProfile = intval(trim($request[2]));
                $roomindex = intval(trim($request[3]));
                $result = query($conn, "SELECT map FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = $row->map;
                    $map = base64_decode($map);
                    $map = json_decode($map);
                    $profile = $map->profiles[$currentProfile];
                    $profile->rooms[$roomindex]->advance = '-';
                    $map = json_encode($map);
                    $map = base64_encode($map);
                    query($conn, "UPDATE systems SET map='$map' WHERE mac='$mac'");
//                     logger("UPDATE systems SET map='$map' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC $mac and password $password do not match any record.\"}";
                }
                break;

            case 'boost':
                // Handle a 'boost' request (sent by controller)
                // Endpoint: {site root}/resources/php/rest.php/boost/{mac}/{password}/{profile}/{roomindex}/{target}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $currentProfile = intval(trim($request[2]));
                $roomIndex = intval(trim($request[3]));
                $target = intval(trim($request[4]));
                $result = query($conn, "SELECT map FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = $row->map;
                    $map = base64_decode($map);
                    $map = json_decode($map);
                    $profile = $map->profiles[$currentProfile];
                    $profile->rooms[$roomIndex]->boost = $target;
                    // Deal with boost end
                    if ($target == 0) {
                        $profile->rooms[$roomIndex]->mode = $profile->rooms[$roomIndex]->prevmode;
                    }
                    $map = json_encode($map);
                    $map = base64_encode($map);
                    logger("UPDATE systems SET map='$map' WHERE mac='$mac'");
                    query($conn, "UPDATE systems SET map='$map' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
                    logger("Boost request failed: MAC $mac and password $password do not match any record.\n");
                    print "{\"message\":\"MAC $mac and password $password do not match any record.\"}";
                }
                break;

            case 'managed':
                // Save the list of systems managed by this user
                // Endpoint: {site root}/resources/php/rest.php/managed/{email}/{password}
                $email = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM users WHERE email='$email' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    mysqli_free_result($result);
                    $systems = file_get_contents("php://input");
                    $encoded = base64_encode($systems);
                    query($conn, "UPDATE users SET systems='$encoded' WHERE email='$email'");
                    // Also write to the 'managed' table
                    query($conn, "DELETE FROM managed WHERE email='$email'");
                    foreach(json_decode($systems, true) as $name=>$values)
                    {
                        $mac = $values["mac"];
                        $pwd = $values["password"];
                        // print "INSERT INTO managed (mac,password,email) VALUES ('$mac',$pwd,'$email')\n";
                        query($conn, "INSERT INTO managed (mac,password,email) VALUES ('$mac',$pwd,'$email')");
                    }
                } else {
                    http_response_code(404);
                    logger("'Managed' failed: Email $email and password $password do not match any record.\n");
                    print "{\"message\":\"Email $email and password $password do not match any record.\"}";
                }
                break;

            case 'psu':
                // Set a flag for the PSU to start (S), halt (H) or reboot (R)
                // Endpoint: {site root}/resources/php/rest.php/psu/<mac>/{password}/{flag}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $flag = trim($request[2])[0];
                $result = query($conn, "SELECT psu FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    mysqli_free_result($result);
                    query($conn, "UPDATE systems SET psu='$flag' WHERE mac='$mac'");

                    // Use the 'managed' table to find the user email, then send notifications.
                    $result = query($conn, "SELECT email FROM managed WHERE mac='$mac'");
                    while ($row = mysqli_fetch_object($result)) {
                        $email = $row->email;
                        $data = new stdClass();
                        $data->sender = "RBR admin";
                        $data->email = $email;
                        $data->subject = "RBR power supply message";
                        $data->message = "Received PSU code $flag for system $mac ";
                        $data->smtpusername = $smtpusername;
                        $data->smtppassword = $smtppassword;
                        try {
                            sendMail($data);
                            print "Email sent to $email\n";
                        } catch (Exception $e) {
                            http_response_code(404);
                            print "{\"message\": $data->err}";
                            break;
                        }
                    }
                    mysqli_free_result($result);
                } else {
                    http_response_code(404);
                    print "MAC '$mac' and password '$password' do not match any record.";
                }
                break;

            default:
                http_response_code(404);
                print "{\"message\":\"Unrecognised action '$action' requested.\"}";
                break;
        }
    }

    /////////////////////////////////////////////////////////////////////////
    // Do an SQL query
    function query($conn, $sql)
    {
       // logger("$sql\n");
        $result = mysqli_query($conn, $sql);
        if (!$result) {
            http_response_code(404);
            logger("Error in $sql: ".mysqli_error($conn));
            die('Error: '.mysqli_error($conn));
        }
        return $result;
    }

    ////////////////////////////////////////////////////////////////////////////
    // Log a message.
    function logger($message)
    {
        return;
        // print("$message\n");
        $timestamp = time();
        $date = date("Y/m/d H:i", $timestamp);
        if (!file_exists("log")) mkdir("log");
        $file = "log/".date("Y", $timestamp);
        if (!file_exists($file)) mkdir($file);
        $file.= "/".date("Ymd", $timestamp).".txt";
        $fp = fopen($file, "a+") or die("Can't open $file");
        fwrite($fp, "$date: $message\n");
        fclose($fp);
    }

    ////////////////////////////////////////////////////////////////////////////
    // Send an email.
    function sendMail($data)
    {
        // print_r($data);
        $mail = new PHPMailer(true);                              // Passing `true` enables exceptions
        try {
            //Server settings
            $mail->SMTPDebug = 0;                                 // Enable verbose debug output
            $mail->isSMTP();                                      // Set mailer to use SMTP
            $mail->Host = 'smtp.dreamhost.com';                   // Specify main and backup SMTP servers
            $mail->SMTPAuth = true;                               // Enable SMTP authentication
            $mail->Username = $data->smtpusername;                // SMTP username
            $mail->Password = $data->smtppassword;                // SMTP password
            $mail->SMTPSecure = 'ssl';                            // Enable SSL encryption, TLS also accepted with port 465
            $mail->Port = 465;                                    // TCP port to connect to

            //Recipients
            $mail->setFrom('admin@rbrheating.com', $data->sender);          //This is the email your form sends From
            //$mail->addAddress($email, 'Joe User'); // Add a recipient address
            $mail->addAddress($data->email);               // Name is optional
            //$mail->addReplyTo('info@example.com', 'Information');
            //$mail->addCC('cc@example.com');
            //$mail->addBCC('bcc@example.com');

            //Attachments
            //$mail->addAttachment('/var/tmp/file.tar.gz');         // Add attachments
            //$mail->addAttachment('/tmp/image.jpg', 'new.jpg');    // Optional name

            //Content
            $mail->isHTML(true);                                  // Set email format to HTML
            $mail->Subject = $data->subject;
            $mail->Body    = $data->message;
            //$mail->AltBody = 'This is the body in plain text for non-HTML mail clients';

            $mail->send();
            //echo 'Message has been sent';
        } catch (Exception $e) {
            // print 'Mailer Error: ' . $mail->ErrorInfo;
            $data->err = 'Mailer Error: ' . $mail->ErrorInfo;
            throw $e;
        }
    }
?>
