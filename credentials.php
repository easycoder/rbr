<?php
header('Content-Type: application/json');

$file = '../' . $_SERVER['HTTP_HOST'] . '.txt';

if (!file_exists($file)) {
    http_response_code(404);
    echo json_encode(['error' => 'Credentials not found']);
    exit;
}

echo trim(file_get_contents($file));
