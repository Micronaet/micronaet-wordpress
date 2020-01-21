<?php
    // Parameters:
    $name = $_GET["name"];

    // Create extra parameters:    
    $filename = "./images/$name.jpg";
    $mime_type = mime_content_type($filename);

    //Return procedure:
    if (file_exists($filename)) {
        header($_SERVER["SERVER_PROTOCOL"] . " 200 OK");
        header("Cache-Control: private"); // Needed for internet explorer
        header("Content-Type: $mime_type");
        //header("Content-Transfer-Encoding: Binary");
        header("Content-Length:".filesize($filename));
        //header("Content-Disposition: attachment; filename=\"$name\"");
        //readfile($filename);
        $fp = fopen($filename, 'rb');
        fpassthru($fp);
        //die();
    } else {
        die("Error: File not found: $filename");
    }
?>

