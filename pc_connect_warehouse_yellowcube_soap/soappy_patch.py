# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from SOAPpy import HTTPTransport, Config, SOAPAddress, HTTPWithTimeout, SOAPUserAgent
import urllib
from types import *
import re
import base64
import socket, httplib
from httplib import HTTPConnection, HTTP
import Cookie

# SOAPpy modules
from SOAPpy.Errors      import *
from SOAPpy.Config      import Config
from SOAPpy.Parser      import parseSOAPRPC
from SOAPpy.SOAPBuilder import buildSOAP
from SOAPpy.Utilities   import *
from SOAPpy.Types       import faultType, simplify
from SOAPpy.version import __version__


def __patched_HTTPTransport_call(self, addr, data, namespace, soapaction = None, encoding = None,
    http_proxy = None, config = Config, timeout=None):

    def __addcookies(self, r):
        '''Add cookies from self.cookies to request r
        '''
        for cname, morsel in self.cookies.items():
            attrs = []
            value = morsel.get('version', '')
            if value != '' and value != '0':
                attrs.append('$Version=%s' % value)
            attrs.append('%s=%s' % (cname, morsel.coded_value))
            value = morsel.get('path')
            if value:
                attrs.append('$Path=%s' % value)
            value = morsel.get('domain')
            if value:
                attrs.append('$Domain=%s' % value)
            r.putheader('Cookie', "; ".join(attrs))

    if not isinstance(addr, SOAPAddress):
        addr = SOAPAddress(addr, config)

    # Build a request
    if http_proxy:
        real_addr = http_proxy
        real_path = addr.proto + "://" + addr.host + addr.path
    else:
        real_addr = addr.host
        real_path = addr.path

    if addr.proto == 'httpg':
        from pyGlobus.io import GSIHTTP
        r = GSIHTTP(real_addr, tcpAttr = config.tcpAttr)
    elif addr.proto == 'https':
        r = httplib.HTTPS(real_addr, key_file=config.SSL.key_file, cert_file=config.SSL.cert_file)
    else:
        r = HTTPWithTimeout(real_addr, timeout=timeout)

    r.putrequest("POST", real_path)

    r.putheader("Host", addr.host)
    r.putheader("User-agent", SOAPUserAgent())
    t = 'text/xml';
    if encoding != None:
        t += '; charset=%s' % encoding
    r.putheader("Content-type", t)
    r.putheader("Content-length", str(len(data)))
    __addcookies(self, r);
    
    # if user is not a user:passwd format
    #    we'll receive a failure from the server. . .I guess (??)
    if addr.user != None:
        val = base64.encodestring(urllib.unquote_plus(addr.user))
        r.putheader('Authorization','Basic ' + val.replace('\012',''))

    # This fixes sending either "" or "None"
    if soapaction == None or len(soapaction) == 0:
        r.putheader("SOAPAction", "")
    else:
        r.putheader("SOAPAction", '"%s"' % soapaction)

    if config.dumpHeadersOut:
        s = 'Outgoing HTTP headers'
        debugHeader(s)
        print "POST %s %s" % (real_path, r._http_vsn_str)
        print "Host:", addr.host
        print "User-agent: SOAPpy " + __version__ + " (http://pywebsvcs.sf.net)"
        print "Content-type:", t
        print "Content-length:", len(data)
        print 'SOAPAction: "%s"' % soapaction
        debugFooter(s)

    # PATCH: Show stream before trying to send-it
    if config.dumpSOAPOut:
        s = 'Outgoing SOAP'
        debugHeader(s)
        print data,
        if data[-1] != '\n':
            print
        debugFooter(s)

    r.endheaders()

    # send the payload
    r.send(data)

    # read response line
    code, msg, headers = r.getreply()

    self.cookies = Cookie.SimpleCookie();
    if headers:
        content_type = headers.get("content-type","text/xml")
        content_length = headers.get("Content-length")

        for cookie in headers.getallmatchingheaders("Set-Cookie"):
            self.cookies.load(cookie);

    else:
        content_type=None
        content_length=None

    # work around OC4J bug which does '<len>, <len>' for some reaason
    if content_length:
        comma=content_length.find(',')
        if comma>0:
            content_length = content_length[:comma]

    # attempt to extract integer message size
    try:
        message_len = int(content_length)
    except:
        message_len = -1

    f = r.getfile()
    if f is None:
        raise HTTPError(code, "Empty response from server\nCode: %s\nHeaders: %s" % (msg, headers))

    if message_len < 0:
        # Content-Length missing or invalid; just read the whole socket
        # This won't work with HTTP/1.1 chunked encoding
        data = f.read()
        message_len = len(data)
    else:
        data = f.read(message_len)

    if(config.debug):
        print "code=",code
        print "msg=", msg
        print "headers=", headers
        print "content-type=", content_type
        print "data=", data

    if config.dumpHeadersIn:
        s = 'Incoming HTTP headers'
        debugHeader(s)
        if headers.headers:
            print "HTTP/1.? %d %s" % (code, msg)
            print "\n".join(map (lambda x: x.strip(), headers.headers))
        else:
            print "HTTP/0.9 %d %s" % (code, msg)
        debugFooter(s)

    def startswith(string, val):
        return string[0:len(val)] == val

    if code == 500 and not \
           ( (startswith(content_type, "text/xml") or startswith(content_type, "text/plain")) and message_len > 0 ):
        raise HTTPError(code, msg)

    if config.dumpSOAPIn:
        s = 'Incoming SOAP'
        debugHeader(s)
        print data,
        if (len(data)>0) and (data[-1] != '\n'):
            print
        debugFooter(s)

    if code not in (200, 500):
        raise HTTPError(code, msg)


    # get the new namespace
    if namespace is None:
        new_ns = None
    else:
        new_ns = self.getNS(namespace, data)

    # return response payload
    return data, new_ns


HTTPTransport.call = __patched_HTTPTransport_call


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: