<?php
    // REST server

    $request = explode("/", substr($_SERVER['PATH_INFO'], 1));
    $action = array_shift($request);
    $method = $_SERVER['REQUEST_METHOD'];
    chdir("../..");
    $cwd = getcwd();

    // First, the commands that don't require a database table name.
    switch ($method) {
        case 'GET':
            switch ($action) {
/*
                case 'list':
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
*/

                case 'ping':
                    print "OK";
                    exit;

                case 'register':
                    // Is this needed?
                    print file_get_contents("map");
                    exit;

                case 'map':
                    // Return the mp. Create a default map if necessary.
                    if (!file_exists("map")) {
                        $fp = fopen("map", "w") or die("Can't open $file");
                        fwrite($fp, '{"profiles":[{"name":"Unnamed","rooms":[{"name":"Unnamed","sensor":"","relays":[""],"mode":"off","target":"0.0","events":[]}],"message":"OK"}],"profile":0,"name":"New system"}');
                        fclose($fp);
                    }
                    print file_get_contents("map");
                    exit;

                case 'sensors':
                    // Get the current sensor data
                    $fn = "/mnt/data/sensorData";
                    if (!file_exists($fn)) {
                        $fp = fopen($fn, "w") or die("Can't open $fn");
                        fwrite($fp, '{"actual": 0}');
                        fclose($fp);
                    }
                    print file_get_contents($fn);
                    exit;
            }
            break;
        case 'POST':
            switch ($action) {
                case 'mkdir':
                    // Create a directory
                    // Endpoint: {site root}/easycoder/rest.php/_mkdir
                    header("Content-Type: application/text");
                    $path = stripslashes(file_get_contents("php://input"));
                        logger("Create directory $path");
                    mkdir($path);
                    exit;
                case 'save':
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
                case 'delete':
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
?>
