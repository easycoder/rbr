<?php
    // REST server

    // This small REST server gives you the ability to manage tables
    // in your site database.

    date_default_timezone_set('Europe/London');
//      logger(substr($_SERVER['PATH_INFO'], 1));
    $request = explode("/", substr($_SERVER['PATH_INFO'], 1));
    $action = array_shift($request);
    $method = $_SERVER['REQUEST_METHOD'];

    $props = array();
    $filename = '../' . $_SERVER['HTTP_HOST'] . '.txt';
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
         logger('Properties file not found');
        exit;
    }

    // First, the commands that don't require a database connection.
    switch ($method) {
        case 'GET':
            switch ($action) {
                case '_list':
                    // List the contents of a directory
                    // Endpoint: {site root}/rest.php/_list/[{path}]
//                  Start at the resources folder
                    $path = getcwd() . '/resources/';
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
                    // Endpoint: {site root}/easycoder/rest.php/_exists/{{path}
                    $path = getcwd() . '/resources/' . str_replace('~', '/', $request[0]);
                    print file_exists($path) ? 'Y' : '';
                    exit;
                case '_load':
                    // Load a file from the resources folder
                    // Endpoint: {site root}/easycoder/rest.php/_load/{path}
                    $path = getcwd() . '/resources/' . str_replace('~', '/', $request[0]);
                    print file_get_contents($path);
                    exit;
                case '_loadall':
                    // Load all the files in the named folder
                    // Endpoint: {site root}/easycoder/rest.php/_loadall/{path}
                    $path = getcwd() . '/resources/';
                    if (count($request)) {
                         $path .= str_replace('~', '/', $request[0]);
                    }
                    $files = scandir($path);
                    print '[';
                    $flag = false;
                    foreach ($files as $file) {
                        if (strpos($file, '.') !== 0) {
                            if (!is_dir("$path/$file")) {
                                if ($flag) {
                                    print ',';
                                } else {
                                    $flag = true;
                                }
                                print file_get_contents("$path/$file");
                            }
                        }
                    }
                    print ']';
                    exit;
            }
            break;
    }

    // The remaining commands require use of the database.
    $conn = mysqli_connect($props['sqlhost'], $props['sqluser'],
    $props['sqlpassword'], $props['sqldatabase']);
    if (!$conn)
    {
        http_response_code(404);
        die("Failed to connect to MySQL: " . mysqli_connect_error());
    }
    mysqli_set_charset($conn,'utf8');

    if (!count($request)) {
        http_response_code(400);
        print "{\"message\":\"Incomplete REST query: ".substr($_SERVER['PATH_INFO'], 1).".\"}";
        exit;
    }

     switch ($method) {

        case 'GET':
            get($conn, $action, $request);
            break;

        case 'POST':
            post($conn, $action, $request);
            break;

        default:
            http_response_code(400);
            break;
    }
    mysqli_close();
    exit;

    // GET
    function get($conn, $action, $request) {
        $ts = time();
        switch ($action) {

            // Endpoints called by the system controller and the user

            case 'map':
                // Get the system map, given its MAC.
                // Endpoint: {site root}/rest.php/map/<mac>
                $mac = $request[0];
//                 logger("SELECT map FROM systems WHERE mac='$mac'");
                $result = $conn->query("SELECT map FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    print base64_decode($row->map);
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            // Endpoints called by the system controller

            case 'register':
                // Register a new MAC.
                // Endpoint: {site root}/rest.php/register/<mac>
                $mac = $request[0];
                $result = $conn->query("SELECT password FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $password = $row->password;
                } else {
                    $password = rand(100000, 999999);
                    $map = '{"rooms":[{"name":"","sensor":"","relays":[""],"mode":"off","target":"0.0","events":[]}],"message":"OK"}';
                    $map = base64_encode($map);
                    $conn->query("INSERT INTO systems (ts,mac,password,map) VALUES ('$ts','$mac','$password','$map')");
//                     logger("INSERT INTO systems (ts,mac,password) VALUES ('$ts','$mac','$password')");
                }
                print $password;
                break;

            case 'update':
                // Update sensor values and get the current map.
                // Endpoint: {site root}/rest.php/update/<mac>/<sensors>
                $mac = $request[0];
                $sensors = $request[1];
                $result = $conn->query("SELECT * FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $id = $row->id;
                    $sensors = $conn->real_escape_string(base64_encode($sensors));
                    $conn->query("UPDATE systems SET sensors='$sensors' WHERE id='$id'");
//                     logger("UPDATE systems SET sensors='$sensors' WHERE id=$id");
//                     print("UPDATE systems SET sensors='$sensors' WHERE id=$id"); print "\n";
                    print base64_decode($row->map); print "\n";
                }
                mysqli_free_result($result);
                break;

                // Endpoints called by the user.

            case 'name':
                // Get the system name, given its MAC.
                // Endpoint: {site root}/rest.php/name/<mac>
                $mac = $request[0];
                $result = $conn->query("SELECT name FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    print $row->name;
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            case 'sensors':
                // Get the systems sensor values, given its MAC.
                // Endpoint: {site root}/rest.php/sensors/<mac>
                $mac = $request[0];
                $result = $conn->query("SELECT sensors FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $sensors = $row->sensors;
                    $sensors = base64_decode($sensors);
                    print $sensors;
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            default:
                http_response_code(404);
                print "I don't understand this request.";
                break;
         }
    }

    /////////////////////////////////////////////////////////////////////////
    // POST
    function post($conn, $action, $request) {
        $ts = time();
        switch ($action) {

            case 'register':
                // Register an email address.
                // Endpoint: {site root}/rest.php/register/<address>
                $to = trim($request[0]);
                logger("SELECT password FROM systems WHERE mac='$to'");
                $result = $conn->query("SELECT password FROM systems WHERE mac='$to'");
                if ($row = mysqli_fetch_object($result)) {
                    $password = $row->password;
                } else {
                    $password = rand(100000, 999999);
//                    $conn->query("INSERT INTO systems (ts,mac,password) VALUES ('$ts','$to','$password')");
                     logger("INSERT INTO systems (ts,mac,password) VALUES ('$ts','$to','$password')");
                }
                $from = "admin@rbrcontrol.com";
                $subject = "Room By Room email password";
                $message = "The RBR password for this email address is $password.";
                $headers = "From: $from";
                if (mail($to, $subject, $message, $headers)) {
                    logger("Password $password sent to $to");
                    print "Password $password sent to $to";
                } else {
                    logger("Message failed");
                    print "Message failed";
                }
                break;
            case 'name':
                // Set the system name
                // Endpoint: https://rbr.easycoder.software/rest.php/name/{mac}/{password}/{name}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $name = trim($request[2]);
                $result = $conn->query("SELECT id FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $id = $row->id;
                    $conn->query("UPDATE systems SET name='$name' WHERE id='$id'");
//                     logger("UPDATE systems SET name='$name' WHERE id=$id");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'map':
                // Set the system map
                // Endpoint: https://rbr.easycoder.software/rest.php/map/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = $conn->query("SELECT id FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $id = $row->id;
                    $map = file_get_contents("php://input");
//                    print "$map\n";
                    $map = base64_encode($map);
//                    print "$map\n";
                    $conn->query("UPDATE systems SET map='$map' WHERE id='$id'");
//                     logger("UPDATE systems SET map='$map' WHERE id=$id");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'backup':
                // Set the system backup map
                // Endpoint: https://rbr.easycoder.software/rest.php/backup/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = $conn->query("SELECT id FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $id = $row->id;
                    $map = file_get_contents("php://input");
//                    print "$map\n";
                    $map = base64_encode($map);
//                    print "$map\n";
                    $conn->query("UPDATE systems SET backup='$map' WHERE id='$id'");
//                     logger("UPDATE systems SET backup='$map' WHERE id=$id");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'restore':
                // Restore the system backup, given its MAC
                // Endpoint: https://rbr.easycoder.software/rest.php/restore/<mac>/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
//                 logger("SELECT * FROM systems WHERE mac='$mac'");
                $result = $conn->query("SELECT id,backup FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $id = $row->id;
                    if ($row->backup) {
                        $map = $row->backup;
                        $conn->query("UPDATE systems SET map='$map' WHERE id='$id'");
//                        logger("UPDATE systems SET map='$map' WHERE id=$id");
                        $map = base64_encode($map);
                        print "$map\n";
                    }
                    else {
                        print '';
                    }
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                mysqli_free_result($result);
                break;

            case 'confirm':
                // Confirm receipt of a message
                // Endpoint: https://rbr.easycoder.software/rest.php/confirm/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = $conn->query("SELECT id, map FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $id = $row->id;
                    $map = $row->map;
                    $map = base64_decode($map);
                    $map = json_decode($map);
                    $map->message = "OK";
                    $map = json_encode($map);
                    $map = base64_encode($map);
                    $conn->query("UPDATE systems SET map='$map' WHERE id='$id'");
//                     logger("UPDATE systems SET map='$map' WHERE id=$id");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC $mac and password $password do not match any record.\"}";
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

?>
