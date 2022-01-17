<?php
    // REST server

    // This small REST server gives you the ability to manage tables
    // in your site database.

    date_default_timezone_set('Europe/London');
//     logger(substr($_SERVER['PATH_INFO'], 1));
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
//         logger('Properties file not found');
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
        case 'POST':
            switch ($action) {
                case '_mkdir':
                    // Create a directory
                    // Endpoint: {site root}/easycoder/rest.php/_mkdir
                    header("Content-Type: application/text");
                    $path = stripslashes(file_get_contents("php://input"));
//                     logger("Create directory $path");
                    mkdir($path);
                    exit;
                case '_upload':
                    // Upload a file (an image) to the current directory
                    // Endpoint: {site root}/easycoder/rest.php/_upload
                    $path = $_POST['path'];
                    $pathsegs = explode("/", $path);
                    $path = str_replace('~', '/', $pathsegs[1]);
                    $fileName = $_FILES['source']['name'];
                    $tempName = $_FILES['source']['tmp_name'];
                    $fileType = $_FILES['source']['type'];
                    $fileSize = $_FILES['source']['size'];
                    $fileError = $_FILES['source']['error'];
                    if (!move_uploaded_file($tempName, "$path/$fileName")) {
                        unlink($tempName);
                        http_response_code(400);
//                         logger("Failed to upload $fileName to $path.\ntempName: $tempName\nfileType: $fileType\nfileSize:$fileSize\nfileError: $fileError");
                    } else {
                        logger("File $fileName uploaded successfully to $path/$fileName");
                        $size = getimagesize("$path/$fileName");
                        logger("$path/$fileName: width:".$size[0].", height:".$size[1]);
                        if ($size[0] > 1024) {
                            logger("mogrify -resize 1024x1024 $path/$fileName");
                            systems("mogrify -resize 1024x1024 $path/$fileName");
                        }
                    }
                    exit;
                case '_save':
                    // Save data to a file in the resources folder
                    // Endpoint: {site root}/easycoder/rest.php/_save/{path}
                    $path = getcwd() . '/resources/' . str_replace('~', '/', $request[0]);
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
                    $path = getcwd() . '/resources/' . str_replace('~', '/', $request[0]);
                    if (is_dir($path)) {
                        rmdir($path);
                    } else {
                        unlink($path);
                    }
                    exit;
                case '_email':
                    // Send an email
                    // Endpoint: {site root}/easycoder/rest.php/_email
                    header("Content-Type: application/text");
                    $value = stripslashes(file_get_contents("php://input"));
                    $json = json_decode($value);
                    $from = $json->from;
                    $to = $json->to;
                    $subject = $json->subject;
                    $message = $json->message;
                    $headers = "MIME-Version: 1.0\r\n";
                    $headers .= "Content-Type: text/html; charset=ISO-8859-1\r\n";
                    $headers .= "From: $from\r\n";
                    mail($to, $subject, $message, "$headers\r\n");
                    print "$headers\r\n$message";
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
                // Endpoint: https://rbr.easycoder.software/rest.php/map/<mac>
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
                // Endpoint: https://rbr.easycoder.software/rest.php/register/<mac>
                $mac = $request[0];
                $result = $conn->query("SELECT * FROM systems WHERE mac='$mac'");
                if (!$row = mysqli_fetch_object($result)) {
                    $password = rand(100000, 999999);
                    $conn->query("INSERT INTO systems (ts,mac,password) VALUES ('$ts','$mac','$password')");
//                     logger("INSERT INTO systems (ts,mac,password) VALUES ('$ts','$mac','$password')");
                    print $password;
                }
                break;

            case 'update':
                // Update sensor values and get the current map.
                // Endpoint: https://rbr.easycoder.software/rest.php/update/<mac>/<sensors>
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

//                 $mac = $request[0];
//                 $result = $conn->query("SELECT sensors FROM systems WHERE mac='$mac'");
//                 if ($row = mysqli_fetch_object($result)) {
//                     $sensors = $row->sensors;
//                     $sensors = base64_decode($sensors);
//                     print $sensors;
//                 } else {
//                     print '';
//                 }
//                 mysqli_free_result($result);
                break;

                // Endpoints called by the user.

            case 'name':
                // Get the system name, given its MAC.
                // Endpoint: https://rbr.easycoder.software/rest.php/name/<mac>
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
                // Endpoint: https://rbr.easycoder.software/rest.php/sensors/<mac>
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

            case 'name':
                // Set the system name
                // Endpoint: https://rbr.easycoder.software/rest.php/name/{mac}/{name}
                $mac = $request[0];
                $name = $request[1];
                $result = $conn->query("SELECT id FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $id = $row->id;
                    $conn->query("UPDATE systems SET name='$name' WHERE id='$id'");
//                     logger("UPDATE systems SET name='$name' WHERE id=$id");
                }
                break;

            case 'map':
                // Set the system map
                // Endpoint: https://rbr.easycoder.software/rest.php/map/
                $mac = $request[0];
                $name = $request[1];
                $result = $conn->query("SELECT id FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $id = $row->id;
                    $map = file_get_contents("php://input");
                    print "$map\n";
                    $map = base64_encode($map);
                    print "$map\n";
                    $conn->query("UPDATE systems SET map='$map' WHERE id='$id'");
//                     logger("UPDATE systems SET map='$map' WHERE id=$id");
                }
                break;

            case 'mode':
                // Set the mode of a room: on/off/auto
                // Endpoint: https://rbr.easycoder.software/rest.php/mode/{mac}/{name}/{mode}
                $mac = $request[0];
                $name = $request[1];
                $mode = $request[2];
                $result = $conn->query("SELECT id, map FROM systems WHERE mac='$mac'");
                if ($row = mysqli_fetch_object($result)) {
                    $id = $row->id;
                    $map = $row->map;
                    $map = base64_decode($map);
                    $map = json_decode($map);
                    $rooms = $map->rooms;
                    for ($r = 0; $r < count($rooms); $r++) {
                        $room = $rooms[$r];
                        if ($room->name == $name) {
                            $room->mode = $mode;
                            $map->message = 'confirm';
                            $map = json_encode($map);
                            print "$map\n";
                            $map = base64_encode($map);
                            $conn->query("UPDATE systems SET map='$map' WHERE id='$id'");
//                             logger("UPDATE systems SET map='$map' WHERE id=$id");
                            break;
                        }
                    }
                }
                break;

            case 'confirm':
                // Confirm receipt of a message
                // Endpoint: https://rbr.easycoder.software/rest.php/confirm/{mac}
                $mac = $request[0];
                $result = $conn->query("SELECT id, map FROM systems WHERE mac='$mac'");
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
