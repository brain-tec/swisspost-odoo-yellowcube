<?php

require 'wse-php/soap-wsa.php';
require 'wse-php/soap-wsse.php';


$keyfile = stream_get_line(STDIN, 1024, PHP_EOL);
$certfile = stream_get_line(STDIN, 1024, PHP_EOL);
# echo "<!-- Waiting for input -->";
$request = '';

do {
	$last = stream_get_line(STDIN, 8096, PHP_EOL);
	if ($last) {
		$request .= $last;
		$request .= PHP_EOL;
	};
} while ($last);

# echo "<!-- result -->";


$doc = new \DOMDocument();
$doc->loadXML($request);
$wsse = new WSSESoap($doc);
$wsse->addTimestamp();
$key = new XMLSecurityKey(XMLSecurityKey::RSA_SHA1, array('type'=>'private'));
$key->loadKey($keyfile, TRUE);
$wsse->signSoapDoc($key);
$token = $wsse->addBinaryToken(file_get_contents($certfile));
$wsse->attachTokentoSig($token);
echo $wsse->saveXML();

#echo $input;

# echo "<!-- EOF -->";

?>