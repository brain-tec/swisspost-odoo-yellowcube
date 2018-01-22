# -*- coding: utf-8 -*-
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.


class APIException(Exception):
    pass


class ProfileNotFound(APIException):
    pass


class TooManyProfiles(APIException):
    pass
