<?php
    // REST server

    date_default_timezone_set('Europe/London');

    $request = $_REQUEST;
    // print_r($_REQUEST); print "\n";
    $action = array_keys($_REQUEST)[0];
//    print "$action\n";
    $data = $_REQUEST[$action];
    // print "$data\n";
    $method = $_SERVER['REQUEST_METHOD'];
    print "method = $method, action = $action, data=$data\n";

    switch ($method) {
        case 'GET':
            switch ($action) {
                case 'list':
                    // List the contents of a directory
                    // Endpoint: {site root}?list={path}

                    $files = scandir($data);
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
            }
        }

/*
                case 'hash':
                    // Get a hash of a value
                    // Endpoint: {site root}/easycoder/rest.php/_hash/{value-to-hash}
                    print password_hash($request[0], PASSWORD_DEFAULT);
                    exit;
                case 'verify':
                    // Verify a hash
                    // Endpoint: {site root}/easycoder/rest.php/_verify/{value-to-verify}
                    print password_verify($request[0], $props['password']) ? 'yes' : 'no';
                    exit;
                case 'exists':
                    // Test if a file exists
                    // Endpoint: {site root}/easycoder/rest.php/_exists/{path}
                    $path = $cwd . '/resources/' . str_replace('~', '/', $request[0]);
                    print file_exists($path) ? 'Y' : '';
                    exit;
                case 'test':
                    // Endpoint: {site root}/easycoder/rest.php/_test/
                    print_r($_SERVER[SERVER_NAME]);
                    exit;
*/
/*
            }
            break;
*/
/*
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
                        $path = 'resources/' . str_replace('~', '/', $request[0]);
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
                        $path = 'resources/' . str_replace('~', '/', $request[0]);
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
*/
/*
        }
    }
*/

    ////////////////////////////////////////////////////////////////////////////
    // Log a message.
/*
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
    */
?>
