<?php
    // REST server

    // This small REST server gives you the ability to manage tables
    // in your site database.
    use PHPMailer\PHPMailer\PHPMailer;
    use PHPMailer\PHPMailer\Exception;

    require '/home/rbrheating/PHPMailer/src/Exception.php';
    require '/home/rbrheating/PHPMailer/src/PHPMailer.php';
    require '/home/rbrheating/PHPMailer/src/SMTP.php';

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
                    // Endpoint: {site root}/resources/php/rest.php/_hash/{value-to-hash}
                    print password_hash($request[0], PASSWORD_DEFAULT);
                    exit;
                case '_verify':
                    // Verify a hash
                    // Endpoint: {site root}/resources/php/rest.php/_verify/{value-to-verify}
                    print password_verify($request[0], $props['password']) ? 'yes' : 'no';
                    exit;
                case '_exists':
                    // Test if a file exists
                    // Endpoint: {site root}/resources/php/rest.php/_exists/{path}
                    $path = $cwd . '/resources/' . str_replace('~', '/', $request[0]);
                    print file_exists($path) ? 'Y' : '';
                    exit;
                case '_test':
                    // Endpoint: {site root}/resources/php/rest.php/_test/
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
                        // Endpoint: {site root}/resources/php/rest.php/_mkdir
                        header("Content-Type: application/text");
                        $path = stripslashes(file_get_contents("php://input"));
                         logger("Create directory $path");
                        mkdir($path);
                        exit;
                    case '_save':
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
                    case '_delete':
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
                $xpassword = "x$password";
                $result = query($conn, "SELECT null FROM users WHERE email='$email' AND password='$xpassword'");
                logger("SELECT null FROM user WHERE email='$email' AND password='$xpassword'");
                if ($row = mysqli_fetch_object($result)) {
                    $message = "You are now registered with RBR Heating with the following credentials:<br><br>"
                        . "User name: $email<br>"
                        . "Password: $password<br><br>"
                        . "Please save these details. You should only need them if you change to a different browser "
                        . "or use a different device to access RBR Heating.";
                    $data = new stdClass();
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
    function post($conn, $action, $request, $smtpusername, $smtppassword) {
        $ts = time();
        switch ($action) {

            case 'stock':
                // Handle a stock request.
                // Endpoint: {site root}/resources/php/rest.php/stock/save
                $opcode = $request[0];
                $data = file_get_contents("php://input");
                $data = json_decode($data);
                $code = $data->code;
                $name = $data->name;
                $source = $data->source;
                $packsize = $data->packsize;
                $packprice = $data->packprice;
                $postage = $data->postage;
                $stock = $data->stock;
                $notes = $data->notes;
                $result = query($conn, "SELECT null FROM stock WHERE code='$code'");
                if ($row = mysqli_fetch_object($result)) {
                    query($conn, "UPDATE stock SET name='$name', source='$source', packsize=$packsize, packprice=$packprice, postage=$postage, stock=$stock, notes='$notes' WHERE code='$code'");
                    logger("UPDATE stock SET name='$name', source='$source', packsize=$packsize, packprice=$packprice, postage=$postage, stock=$stock, notes='$notes' WHERE code='$code'");
                } else {
                    query($conn, "INSERT INTO stock (code, name, source, packsize, packprice, postage, stock, notes) VALUES ('$code','$name', '$source', $packsize, $packprice, $postage, $stock, '$notes')");
                    logger("INSERT INTO stock (code, name, source, packsize, packprice, postage, stock, notes) VALUES ('$code','$name', '$source', $packsize, $packprice, $postage, $stock, '$notes')");
                break;
                }

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
            $mail->setFrom('admin@rbrheating.com', 'From');          //This is the email your form sends From
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
