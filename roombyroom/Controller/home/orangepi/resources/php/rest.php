<?php
    // REST server

    $request = explode("/", substr($_SERVER['PATH_INFO'], 1));
    $action = array_shift($request);
    $method = $_SERVER['REQUEST_METHOD'];
    chdir("../..");
    $cwd = getcwd();

    switch ($method) {
        case 'GET':
            switch ($action) {

                case 'ping':
                    print "OK";
                    exit;

                case 'register':
                    // Is this needed?
                    print file_get_contents("/mnt/data/map");
                    exit;

                case 'map':
                    // Return the map. Create a default map if necessary.
                    if (!file_exists("/mnt/data/map")) {
                        $fp = fopen("/mnt/data/map", "w") or die("Can't open /mnt/data/map");
                        fwrite($fp, '{"profiles":[{"name":"Unnamed","rooms":[{"name":"Unnamed","sensor":"","relays":[""],"mode":"off","target":"0.0","events":[]}],"message":"OK"}],"profile":0,"name":"New system"}');
                        fclose($fp);
                    }
                    print file_get_contents("/mnt/data/map");
                    exit;

                case 'poll':
                    $args = array();
                    parse_str($_SERVER['QUERY_STRING'], $args);
                    $fp = fopen("/mnt/data/incoming", "w") or die("Can't open '/mnt/data/incoming'");
                    fwrite($fp, $args["data"]);
                    fclose($fp);
                    print file_get_contents("/mnt/data/outgoing", "r");
                    exit;

                case 'getFile':
                    // http://{ipaddr}/resources/php/rest.php/getFile?data={filename}
                    $args = array();
                    parse_str($_SERVER['QUERY_STRING'], $args);
                    print file_get_contents($args["data"]);
                    exit;

                case 'sensors':
                    print file_get_contents("/mnt/data/sensorData");
                    exit;

                case 'notify':
                    // Accept messages from H&T sensors in the form
                    // http://{ipaddr}/resources/php/rest.php/notify?hum=40&temp=20.10&bat=99
                    $source = $_SERVER["REMOTE_ADDR"];
                    $queries = array();
                    parse_str($_SERVER['QUERY_STRING'], $queries);
                    $temp = round($queries["temp"], 1);
                    $bat = $queries["bat"];
                    if (!$bat) $bat = "100";
                    $dir = "/mnt/data/sensors";
                    if (!file_exists($dir)) {
                        mkdir($dir, 0777, true);
                    }
                    $path = "$dir/$source.txt";
                    $ts = time();
                    $message = "{\"temperature\": $temp, \"timestamp\": $ts, \"battery\": $bat}";
                    // print "$message\n";
                    $fp = fopen($path, "w") or die("Can't open '$file'");
                    fwrite($fp, $message);
                    fclose($fp);
                    chmod($path, 0666);
                    print "OK";
                    exit;

                default:
                    http_response_code(404);
                    print "I don't understand $request.";
                    break;

            }
            break;
        case 'POST':
            switch ($action) {
                case 'map':
                    // Set the system map
                    $map = file_get_contents("php://input");
                    $fp = fopen("/mnt/data/map", "w") or die("Can't open map");
                    fwrite($fp, $map);
                    fclose($fp);
                    break;

                case 'request':
                    $request = stripslashes(file_get_contents("php://input"));
                    $fp = fopen("/mnt/data/request", "w") or die("Can't open /mnt/data/request");
                    fwrite($fp, $request);
                    fclose($fp);
                    chmod("/mnt/data/request", 0777);
                    exit;

                case 'response':
                    $response = stripslashes(file_get_contents("php://input"));
                    $fp = fopen("/mnt/data/response", "w") or die("Can't open /mnt/data/response");
                    fwrite($fp, $response);
                    fclose($fp);
                    chmod("/mnt/data/response", 0777);
                    $fp = fopen("/mnt/data/response-ts", "w") or die("Can't open /mnt/data/response-ts");
                    $ts = time();
                    fwrite($fp, "$ts");
                    fclose($fp);
                    chmod("/mnt/data/response-ts", 0777);
                    exit;

                case 'error':
                    $message = stripslashes(file_get_contents("php://input"));
                    $fp = fopen("/mnt/data/errorLog", "a") or die("Can't open /mnt/data/errorLog");
                    $time = time();
                    fwrite($fp, date('r', time()) . ": $message\n");
                    fclose($fp);
                    exit;

                case 'delreq':
                    unlink("/mnt/data/request");
                    exit;

                case 'delresponse':
                    unlink("/mnt/data/response");
                    exit;

                case 'delTempMap':
                    unlink("/mnt/data/map");
                    exit;

                case 'backup':
                    $map = file_get_contents("map");
                    $fp = fopen("backup", "w") or die("Can't open backup");
                    fwrite($fp, $map);
                    fclose($fp);
                    exit;

                case 'restore':
                    if (!file_exists("backup")) {
                        $map = file_get_contents("backup");
                        $fp = fopen("/mnt/data/map", "w") or die("Can't open map");
                        fwrite($fp, $map);
                        fclose($fp);
                    }
                    exit;

                case 'mkdir':
                    // Create a directory
                    // Endpoint: {site root}/resources/php/rest.php/_mkdir
                    header("Content-Type: application/text");
                    $path = stripslashes(file_get_contents("php://input"));
                    mkdir($path);
                    exit;

                case 'save':
                    // Save data to a file in the resources folder
                    // Endpoint: {site root}/resources/php/rest.php/_save/{path}
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

                case 'delete':
                    // Delete a file in the resources folder
                    // Endpoint: {site root}/resources/php/rest.php/_delete/{path}
                    $path = $cwd . '/resources/' . str_replace('~', '/', $request[0]);
                    if (is_dir($path)) {
                        rmdir($path);
                    } else {
                        unlink($path);
                    }
                    exit;

                default:
                    http_response_code(404);
                    print "I don't understand $request.";
                    break;

            }
            break;
    }
?>
