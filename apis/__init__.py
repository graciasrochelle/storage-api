#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from flask_restplus import Api

from .ceph import api as ceph
from .netapp import api as netapp

sso_authorisation = {
    'type': 'shibboleth',
    'flow': 'accessCode',
    'tokenUrl': 'https://borkbork/login'
}


__version__ = '1.0.0'

api = Api(
    title='CERN Unified Storage API',
    version=__version__,
    description='A unified storage API for all data-storage back-ends.',
    authorizations={'sso': sso_authorisation},
    validate=True,
)

api.add_namespace(ceph)
api.add_namespace(netapp)
