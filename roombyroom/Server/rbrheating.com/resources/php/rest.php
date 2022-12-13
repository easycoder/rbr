<?php
    // REST server

    // This small REST server gives you the ability to manage tables
    // in your site database.

    require_once "statistics.php";

    date_default_timezone_set('Europe/London');
//      logger(substr($_SERVER['PATH_INFO'], 1));
    $request = explode("/", substr($_SERVER['PATH_INFO'], 1));
    $action = array_shift($request);
    $method = $_SERVER['REQUEST_METHOD'];
    chdir("../..");
    $cwd = getcwd();

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
         logger("Properties file $filename not found");
         print("Properties file $filename not found");
        exit;
    }

    // First, the commands that don't require a database connection.
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
    //                     logger("Create directory $path");
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
            get($conn, $action, $request);
            break;

        case 'POST':
            post($conn, $action, $request);
            break;

        default:
            http_response_code(400);
            break;
    }
    mysqli_close($conn);
    exit;

    // GET
    function get($conn, $action, $request) {
        $ts = time();
        switch ($action) {

            // Endpoints called by the system controller and the user

            case 'map':
                // Get the system map, given its MAC.
                // Endpoint: {site root}/resources/php/rest.php/map/<mac>
                $mac = $request[0];
                print " ";
                $result = query($conn, "SELECT map FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    print base64_decode($row->map);
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            // Endpoints called by the system controller

            case 'register':
                // Register a new MAC and get the password.
                // Endpoint: {site root}/resources/php/rest.php/register/<mac>
                $mac = trim($request[0]);
                $result = query($conn, "SELECT password FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $password = $row->password;
                } else {
                    $password = rand(100000, 999999);
                    $map = '{"profiles":[{"name":"Unnamed","rooms":[{"name":"Unnamed","sensor":"","relays":[""],"mode":"off","target":"0.0","events":[]}],"message":"OK"}],"profile":0}';
                    $map = base64_encode($map);
                    query($conn, "INSERT INTO systems (ts,mac,password,map) VALUES ('$ts','$mac','$password','$map')");
//                     logger("INSERT INTO systems (ts,mac,password) VALUES ('$ts','$mac','$password')");
                }
                $file = fopen('resources/version', 'r');
                $version = trim(fgets($file));
                fclose($file);
                print '{"password":"'.$password.'","version":"'.$version.'"}';
                break;

            case 'update':
                // Update sensor values and get the current map.
                // This also records statistics.
                // Endpoint: {site root}/resources/php/rest.php/update/<mac>/<sensors>
                $mac = $request[0];
                $sensors = $request[1];

                $daysec = 24*60*60;
                $day = intval($ts / $daysec) * $daysec;

                $data = json_decode($sensors);
                foreach($data as $sensor=>$value) {
                    $relay = $value->relay;
                    $previous = "off";
                    // Update the relay states table
                    $res = query($conn, "SELECT relay from relays WHERE mac='$mac' AND sensor='$sensor'");
                    if ($r = mysqli_fetch_object($res)) {
                        $previous = $r->relay;
                        //print("UPDATE relays SET relay='$relay' WHERE mac='$mac' AND sensor='$sensor'\n");
                        query($conn, "UPDATE relays SET relay='$relay' WHERE mac='$mac' AND sensor='$sensor'");
                    } else {
                        query($conn, "INSERT INTO relays (mac,sensor,relay) VALUES ('$mac','$sensor','$relay')");
                    }
                    mysqli_free_result($res);
                    // Update the stats table
                    if ($previous == "off" && $relay =="on") {
                        // Mark the start of a timing period
                        $res = query($conn, "SELECT null FROM stats WHERE day=$day AND mac='$mac' AND sensor='$sensor'");
                        if ($r = mysqli_fetch_object($res)) {
                            query($conn, "UPDATE stats SET start='$ts' WHERE day=$day AND mac='$mac' AND sensor='$sensor'");
                        } else {
                            // logger("INSERT INTO stats (day,mac,sensor,start,duration) VALUES ($day,'$mac','$sensor','$ts',0)");
                            query($conn, "INSERT INTO stats (day,mac,sensor,start,duration) VALUES ($day,'$mac','$sensor','$ts',0)");
                        }
                    }
                    else if ($previous == "on" && $relay =="off") {
                        // Add the period to the total duration for this day
                        $res = query($conn, "SELECT start, duration FROM stats WHERE day=$day AND mac='$mac' AND sensor='$sensor'");
                        if ($r = mysqli_fetch_object($res)) {
                            $duration = ($ts - $r->start + ($r->duration * 60)) / 60;
                            query($conn, "UPDATE stats SET duration='$duration' WHERE day=$day AND mac='$mac' AND sensor='$sensor'");
                        }
                    }
                }
                // Write the sensor values
                $sensors = $conn->real_escape_string(base64_encode($sensors));
                $result = query($conn, "SELECT map FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = base64_decode($row->map);
                    query($conn, "UPDATE systems SET sensors='$sensors' WHERE mac='$mac'");
//                     logger("UPDATE systems SET sensors='$sensors' WHERE mac='$mac'");
//                     print("UPDATE systems SET sensors='$sensors' WHERE mac='$mac'"); print "\n";
                    // Return the current map
                    print "$map\n";
                }
                mysqli_free_result($result);
                break;

                // Endpoints called by the user.

            case 'sensors':
                // Get the systems sensor values, given its MAC.
                // Endpoint: {site root}/resources/php/rest.php/sensors/<mac>
                $mac = $request[0];
//                print $mac;
                $result = query($conn, "SELECT sensors FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $sensors = $row->sensors;
                    $sensors = base64_decode($sensors);
                    print $sensors;
                } else {
                    print '';
                }
                mysqli_free_result($result);
                break;

            case 'stats':
                // Endpoint: {site root}/resources/php/rest.php/stats/{mac}/{action}/...}
                doStatistics($conn, $request);
                break;

            case 'test':
                // A test endpoint
                // Endpoint: {site root}/resources/php/rest.php/test/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    print "Test passed";
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC $mac and password $password do not match any record.\"}";
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
    function post($conn, $action, $request) {
        $ts = time();
        switch ($action) {

            case 'map':
                // Set the system map
                // Endpoint: {site root}/resources/php/rest.php/map/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = file_get_contents("php://input");
                    $map = base64_encode($map);
//                    print "$map\n";
                    query($conn, "UPDATE systems SET map='$map', last=$ts WHERE mac='$mac'");
//                     logger("UPDATE systems SET map='$map' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
//                     logger("SELECT null FROM systems WHERE mac='$mac' AND password='$password'\n");
//                     logger("{\"message\":\"MAC and password do not match any record.\"}");
//                     print "SELECT null FROM systems WHERE mac='$mac' AND password='$password'\n";
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'map-dev':
                // Set the system map
                // Endpoint: {site root}/resources/php/rest.php/map-dev/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = file_get_contents("php://input");
                    $map = base64_encode($map);
//                    print "$map\n";
                    query($conn, "UPDATE systems SET map='$map', last=$ts WHERE mac='$mac'");
//                     logger("UPDATE systems SET map='$map' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
//                     logger("SELECT null FROM systems WHERE mac='$mac' AND password='$password'\n");
//                     logger("{\"message\":\"MAC and password do not match any record.\"}");
//                     print "SELECT null FROM systems WHERE mac='$mac' AND password='$password'\n";
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'backup':
                // Set the system backup map
                // Endpoint: {site root}/resources/php/rest.php/backup/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT null FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = file_get_contents("php://input");
//                    print "$map\n";
                    $map = base64_encode($map);
//                    print "$map\n";
                    query($conn, "UPDATE systems SET backup='$map' WHERE mac='$mac'");
//                     logger("UPDATE systems SET backup='$map' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC and password do not match any record.\"}";
                }
                break;

            case 'restore':
                // Restore the system backup, given its MAC
                // Endpoint: {site root}/resources/php/rest.php/restore/<mac>/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
//                 logger("SELECT backup FROM systems WHERE mac='$mac'");
                $result = query($conn, "SELECT backup FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    if ($row->backup) {
                        $map = $row->backup;
                        query($conn, "UPDATE systems SET map='$map', last=$ts WHERE mac='$mac'");
//                        logger("UPDATE systems SET map='$map' WHERE mac='$mac'");
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
                // Confirm receipt of a message (sent by controller)
                // Endpoint: {site root}/resources/php/rest.php/confirm/{mac}/{password}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $result = query($conn, "SELECT map FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = $row->map;
                    $map = base64_decode($map);
                    $map = json_decode($map);
                    $map->message = "OK";
                    $map = json_encode($map);
                    $map = base64_encode($map);
                    query($conn, "UPDATE systems SET map='$map' WHERE mac='$mac'");
//                     logger("UPDATE systems SET map='$map' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
                    print "{\"message\":\"MAC $mac and password $password do not match any record.\"}";
                }
                break;

            case 'advance':
                // Acknowledge an 'advance' request (sent by controller)
                // Endpoint: {site root}/resources/php/rest.php/advance/{mac}/{password}/{roomindex}
                $mac = trim($request[0]);
                $password = trim($request[1]);
                $roomindex = intval(trim($request[2]));
                $result = query($conn, "SELECT map FROM systems WHERE mac='$mac' AND password='$password'");
                if ($row = mysqli_fetch_object($result)) {
                    $map = $row->map;
                    $map = base64_decode($map);
                    $map = json_decode($map);
                    $profile = $map->profiles[$map->profile];
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
                    // $profile = $map->profiles[$map->profile];
                    $profile = $map->profiles[$currentProfile];
                    $profile->rooms[$roomIndex]->boost = $target;
                    // Deal with boost end
                    if ($target == 0) {
                        $profile->rooms[$roomIndex]->mode = $profile->rooms[$roomIndex]->prevmode;
                    }
                    $map = json_encode($map);
                    $map = base64_encode($map);
                    // logger("UPDATE systems SET map='$map' WHERE mac='$mac'");
                    query($conn, "UPDATE systems SET map='$map' WHERE mac='$mac'");
                } else {
                    http_response_code(404);
                    logger("Boost request failed: MAC $mac and password $password do not match any record.\n");
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

?>
