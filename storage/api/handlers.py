#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2015, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from flask import Flask, request
from flask.ext.restful import Api, Resource
import sys
import re
import logging
import base64
from storage.config import CONFIG
from storage.vendors.BasicStorage import BasicStorage
from storage.vendors.NetAppops import NetAppops
from storage.vendors.NetAppprov import NetAppprov
from storage.vendors.PolicyRulesNetApp import PolicyRulesNetApp
from storage.vendors.StorageException import StorageException

app = Flask(__name__)
api = Api(app)

class PathREST(Resource):
	logger=None
	def __init__(self):
		''' Method definition '''
		if __name__ == '__main__':
			PathREST.logger = logging.getLogger('storage-api-console')
		else:
			PathREST.logger = logging.getLogger('storage-api')
		
			
	def get(self, path):
		bpath=base64.urlsafe_b64decode(path)
		spath=bpath.decode('ascii')
		baseclass=BasicStorage(spath)
		if baseclass.GetType() == "NetApp":
			netapp=NetAppops(spath)
			result=netapp.GetSnapshotsList()
			if result is None:
				StorageRest.logger.debug("we got 0 snapshots")
				return { 'snapshots': 'NONE' }, 200
			PathREST.logger.debug("we got %s snapshots",len(result))
			return  { 'snapshots': result }, 200
	
	def post(self,path):
		bpath=base64.urlsafe_b64decode(path)
		spath=bpath.decode('ascii')
		PathREST.logger.debug("path is: %s",spath)
		
		sname=None
		clone=None
		if 'snapname' in request.form.keys():
			bname=base64.urlsafe_b64decode(request.form['snapname'])
			sname=bname.decode('ascii')
			PathREST.logger.debug("new snapshot name is: %s",sname)
		if 'clone' in request.form.keys():
			PathREST.logger.debug("want a clone")
			clone=request.form['clone']
			
		baseclass=BasicStorage(spath)
		if baseclass.GetType() == "NetApp":
			netapp=NetAppops(spath)
			try:
				if sname is None:
					if clone:
						PathREST.logger.debug("1")
						return { 'snapshot_clone creation ': 'No snapshot provided for clonning'}, 400 
					else:
						result=netapp.CreateSnapshot()
				else:
					PathREST.logger.debug("2")
					if clone:
						result=netapp.CloneSnapshot(sname)

					else:
						result=netapp.CreateSnapshot(sname)
			except Exception as ex:
				PathREST.logger.debug("Exception taken: %s",str(ex))
				return { 'snapshot_clone creation ': 'error ' + str(ex) }, 500

			PathREST.logger.debug("snapshot_clone created")
			if result==0: 
				return { 'snapshot_clone creation ': 'success' }, 200
			if len(result) > 1:
				return { 'snapshot_clone creation ': 'success - junction-path:' + result }, 200


	def delete(self,path):
		bpath=base64.urlsafe_b64decode(path)
		spath=bpath.decode('ascii')
		PathREST.logger.debug("path is: %s",spath)
		
		if 'snapname' in request.form.keys():
			bname=base64.urlsafe_b64decode(request.form['snapname'])
			sname=bname.decode('ascii')
		else:
			PathREST.logger.debug("new snapshot name is: %s",sname)
			return { 'snapshot deletion ': 'snapname missing!!' }, 400
		
		baseclass=BasicStorage(spath)
		if baseclass.GetType() == "NetApp":
			netapp=NetAppops(spath)
			try:
				result=netapp.DeleteSnapshot(sname)
			except Exception as ex:
				PathREST.logger.debug("Exception got error: {0}".format(str(ex)))
				return { 'snapshot deletion ': 'error {0}'.format(str(ex)) }, 400
		
		PathREST.logger.debug("snapshot deleted")
		return { 'snapshot deletion ': 'success' }, 200

		
class VolumeREST(Resource):
	logger=None
	def __init__(self):
		''' Method definition '''
		if __name__ == '__main__':
			VolumeREST.logger = logging.getLogger('storage-api-console')
		else:
			VolumeREST.logger = logging.getLogger('storage-api')	
       
	def get(self,volname):	
		'''Retrieve information of a given volume represented by its mount path at the server. In case there are snapshots available those are also retrieved.'''
		bpath=base64.urlsafe_b64decode(volname)
		spath=bpath.decode('ascii')
		VolumeREST.logger.debug("path is: %s",spath)
		
		baseclass=BasicStorage(spath)
		if baseclass.GetType() == "NetApp":
			netapp=NetAppprov.ExistingVol(spath)
			if not isinstance(netapp,(BasicStorage,NetAppprov)):
				return { 'volume get ': 'error no online volume found' }, 500
			try:
				result=netapp.GetInfoPath()
			except Exception as ex:
				VolumeREST.logger.debug('problem getting volume information' + str(ex))
				return { 'volume get ': 'error ' + str(ex) }, 500
			else:
				if int(result['snap_reserved']) > 0 :
					netapp2=NetAppops(spath)
					snaps=netapp2.GetSnapshotsList()
					if snaps and len(snaps) > 0 :
						 return { 'volume get ': 'success ' + str(result) + "snaps list: " + str(snaps) }, 20	
				return { 'volume get ': 'success ' + str(result) }, 200	
				
	def post(self,volname):
		'''Creation of a new volume.  Some parameters are required:
			-volname
			-clustername e.g. dbnasc
			-initsize: initial size in GB
			-maximumsize: maximum autosize in GB
			-incrementsize: in GB
			-policy: name of the export policy assigned to the volume
			-junctionpath: NFS server access path. Base64 encoded.
			-typeaggr: e.g. hdd-aggr, ssd-aggr, hybrid-aggr
			-snapsenable: 1 -> yes, 0-> no
			-ip: IP. Base64 encoded. 
			-business: e.g. dbod
			-vendor: NetApp, PureStorage, Ceph
		'''
		#'dbnasc','toTo',1,100,1,'vs2sx50','kk','/ORA/dbs00/TOTO','hdd-aggr',1,'199.22.22.22',"dbod"
		if 'vendor' in request.form.keys():
			vendor=request.form['vendor']
			VolumeREST.logger.debug('vendor is: ' + vendor)
		else:
			return { 'volume creation ': 'error: missing parameter vendor' }, 400

		if 'clustername' in request.form.keys():
			clustername=request.form['clustername']
			VolumeREST.logger.debug('clustername is: ' + clustername)
		else:
			return { 'volume creation ': 'error: missing parameter clustername' }, 400
		if not volname:
			return { 'volume creation ': 'error: missing parameter volname' }, 400
		else:
			VolumeREST.logger.debug('volname is: ' + volname)


		if 'initsize' in request.form.keys():
			initsize=request.form['initsize']
			VolumeREST.logger.debug('initsize is:' + str(initsize))
		else:
			return { 'volume creation ': 'error: missing parameter initsize' }, 400

		if 'maximumsize' in request.form.keys():
			maximumsize=request.form['maximumsize']
			VolumeREST.logger.debug('maximumsize is:' + str(maximumsize))
		else:	
			return { 'volume creation ': 'error: missing parameter maximumsize' }, 400

		if 'incrementsize' in request.form.keys():
			incrementsize=request.form['incrementsize']
			VolumeREST.logger.debug('incrementsize is:' + str(incrementsize))
		else:
			return { 'volume creation ': 'error: missing parameter incrementsize' }, 400

		if 'vserver' in request.form.keys():
			vserver=request.form['vserver']
			VolumeREST.logger.debug('vserver is:' + vserver)
		else:
			return { 'volume creation ': 'error: missing parameter vserver' }, 400

		if 'policy' in request.form.keys():
			policy=request.form['policy']
			VolumeREST.logger.debug('policy is:' + policy)
		else:
			return { 'volume creation ': 'error: missing parameter policy' }, 400

		if 'junctionpath' in request.form.keys():
			junctionpath=base64.urlsafe_b64decode(request.form['junctionpath']).decode('ascii')
			VolumeREST.logger.debug('junctionpath is:' + junctionpath)
		else:
			return { 'volume creation ': 'error: missing parameter junctionpath' }, 400

		if 'typeaggr' in request.form.keys():
			typeaggr=request.form['typeaggr']
			VolumeREST.logger.debug('typeaggr is:' + typeaggr)
		else:
			return { 'volume creation ': 'error: missing parameter typeaggr' }, 400
		
		if 'snapenable' not in request.form.keys():
			#default we create volumes with a snapshot reserve area
			snapenable=1
		else:
			snapenable=request.form['snapenable']
		VolumeREST.logger.debug('snapenable is:' + snapenable)

		if 'ip' in request.form.keys():
			ip=base64.urlsafe_b64decode(request.form['ip']).decode('ascii')
		else:
			ip=0
		VolumeREST.logger.debug('ip is:' + str(ip))

		if 'business' in request.form.keys():
			business=request.form['business']
		else:
			business=0
		VolumeREST.logger.debug('business is:' + str(business))
		
		if vendor == 'NetApp':
			netapp=NetAppprov(clustername,volname,initsize,maximumsize,incrementsize,vserver,policy,junctionpath,typeaggr,ip,snapenable,business)
			try:
				result=netapp.CreateVolume()
			except Exception as ex:
				VolumeREST.logger.debug('problem creating volume' + str(ex))
				return { 'volume creation ': 'error ' + str(ex) }, 500
			else:
				if (result==0):
					VolumeREST.logger.debug('Volume %s has been created',volname)
					return { 'volume creation ': 'success' }, 200
				else:
					VolumeREST.logger.debug('Volume %s has failed',volname)
					return { 'volume creation ': 'error creating' + volname }, 500

		else:
			return { 'volume creation ': 'wrong vendor' }, 400

			
	def delete(self,volname):
		''' Deletes a volume. It's represented by its junction path and IP to mount.'''
		bpath=base64.urlsafe_b64decode(volname)
		spath=bpath.decode('ascii')
		VolumeREST.logger.debug("path is: %s",spath)
		
		baseclass=BasicStorage(spath)
		if baseclass.GetType() == "NetApp":
			netapp=NetAppprov.ExistingVol(spath)
			if not isinstance(netapp,(BasicStorage,NetAppprov)):
				return { 'volume deletion ': 'error no online volume found' }, 500
			try:
				result=netapp.DeleteVolume()
			except Exception as ex:
				VolumeREST.logger.debug('problem deleting volume' + str(ex))
				return { 'volume deletion ': 'error ' + str(ex) }, 500
			else:
				if (result==0):
					VolumeREST.logger.debug('Volume %s has been deleted',netapp.volname)
					return { 'volume deletion ': 'success' }, 200
				else:
					VolumeREST.logger.debug('Volume %s deletion has failed',netapp.volname)
					return { 'volume deletion ': 'error deleting' + netapp.volname }, 500

		else:
			return { 'volume deletion ': 'wrong vendor' }, 400
		
		
	def put(self, volname):
		'''Modify autosize. Values should be provided on GB. You can modify maximum autosize and increment'''
		bpath=base64.urlsafe_b64decode(volname)
		spath=bpath.decode('ascii')
		VolumeREST.logger.debug("path is: %s",spath)
		
		if 'maxautosize' in request.form.keys():
			maxautosize=request.form['maxautosize']
		else:
			return { 'volume setautosize ': 'error no maxautosize provided!!' }, 400
		if 'increment' in request.form.keys():
			increment=request.form['increment']
		else:
			increment=0
		
		baseclass=BasicStorage(spath)
		if baseclass.GetType() == "NetApp":
			netapp=NetAppprov.ExistingVol(spath)
			if not isinstance(netapp,(BasicStorage,NetAppprov)):
				return { 'volume setautosize ': 'error no online volume found' }, 500
			
			result=netapp.SetAutoSize(maxautosize,increment)	
			if result==0:
				VolumeREST.logger.debug('autosize [%s,%s] has been set for %s',maxautosize,increment,netapp.volname)
				return { 'volume setautosize ': 'success' }, 200
			else:
				VolumeREST.logger.debug('autosize couldnt be set for volume: %s',netapp.volname)
				return { 'volume setautosize ': 'error: ' + result }, 500

		

class RulesREST(Resource):
	logger=None
	def __init__(self):
		''' Method definition '''
		if __name__ == '__main__':
			RulesREST.logger = logging.getLogger('storage-api-console')
		else:
			RulesREST.logger = logging.getLogger('storage-api')	
       	
	def get(self,path):
		'''Retrieved policy and rules linked to a controller:mountpath tuple'''
		bpath=base64.urlsafe_b64decode(path)
		spath=bpath.decode('ascii')
		RulesREST.logger.debug("path is: %s",spath)
		
		baseclass=BasicStorage(spath)
		if baseclass.GetType() == "NetApp":
			exportpolicy=PolicyRulesNetApp.ExistingVolume(spath)
			try:
				result=exportpolicy.GetRuleAllREST()
			except Exception as ex:
				return { 'rules ops ': 'error: ' + str(ex) }, 500
			else:
				if result is None:
					return { 'rules ops ': 'No rules found' }, 200
				else:
					return { 'rules ops ': 'success ' + str(result) }, 200
	
	def put(self,path):
		''' Add or remove an IP on a given existing policy'''
		bpath=base64.urlsafe_b64decode(path)
		spath=bpath.decode('ascii')
		RulesREST.logger.debug("path is: %s",spath)
		
		baseclass=BasicStorage(spath)
		if baseclass.GetType() == "NetApp":
			exportpolicy=PolicyRulesNetApp.ExistingVolume(spath)

		deleterule=None
		addrule=None
		if 'deleterule' in request.form.keys():
			deleterule=base64.urlsafe_b64decode(request.form['deleterule']).decode('ascii')	
		if 'addrule' in request.form.keys():
			addrule=base64.urlsafe_b64decode(request.form['addrule']).decode('ascii')	
		
		baseclass=BasicStorage(spath)
		if baseclass.GetType() == "NetApp":
			exportpolicy=PolicyRulesNetApp.ExistingVolume(spath)
		
		result=None
		if addrule:
			result=exportpolicy.CreateRuleREST(addrule)
			if result==0:
				return { 'rules ops ': 'success ' + str(addrule) + ' was added.' }, 200
		elif deleterule:
			result=exportpolicy.DeleteRuleREST(deleterule)
			if result==0:
				return { 'rules ops ': 'success ' + str(deleterule) + ' was removed.' }, 200


		return { 'rules ops ': 'noops. Please contact admins'  }, 500
		
		
		
			
	





api.add_resource(PathREST, '/storage/api/v1.0/paths/<string:path>')
api.add_resource(VolumeREST, '/storage/api/v1.0/volumes/<string:volname>')
api.add_resource(RulesREST, '/storage/api/v1.0/exports/<string:path>')

if __name__ == '__main__':
    app.run(debug=True)