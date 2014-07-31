import math, sys

import maya.cmds as cmds

import maya.OpenMaya as OpenMaya
import maya.OpenMayaAnim as OpenMayaAnim
import maya.OpenMayaMPx as OpenMayaMPx

kPluginTypeName = "pbrtExport"

#pbrtExportId = OpenMaya.MTypeId(0x8702)
	
# Node definition
class pbrtExport(OpenMayaMPx.MPxFileTranslator):
	# class variables
	#angle = OpenMaya.MObject()
	#filename = OpenMaya.MObject()

	# constructor
	def __init__(self):
		OpenMayaMPx.MPxFileTranslator.__init__(self)

	def haveReadMethod(self):
		return False

	def haveWriteMethod(self): 
		return True;

	def writer( self, fileObject, optionString, accessMode ):
		try:
			fullName = fileObject.fullName()
			fileHandle = open(fullName,"w")
			fileHandle.write("# Simple text file of custom node information\n")

			# MItDependencyNodes
			iterator=OpenMaya.MItDag()
			while not iterator.isDone():
				object = iterator.currentItem()
				#
				try:
					dnFn = OpenMaya.MFnDependencyNode( object )
					#userNode = dnFn.userNode()
					#if ( not( userNode == None ) ):
					line = "# custom node: " + dnFn.name() + "\n"
					fileHandle.write(line)
				except:
					pass
				iterator.next()
			fileHandle.close()
		except:
			sys.stderr.write( "Failed to write file information\n")
			raise

	def defaultExtension(self):
		return "pbrt"

# creator
def translatorCreator():
	return OpenMayaMPx.asMPxPtr( pbrtExport() )
	
# initialize the script plug-in
def initializePlugin(mobject):
	mplugin = OpenMayaMPx.MFnPlugin(mobject)
	try:
		mplugin.registerFileTranslator( kPluginTypeName, None, translatorCreator )
	except:
		sys.stderr.write( "Failed to register node: %s\n" % kPluginTypeName )
		raise

# uninitialize the script plug-in
def uninitializePlugin(mobject):
	mplugin = OpenMayaMPx.MFnPlugin(mobject)
	try:
		mplugin.deregisterFileTranslator( kPluginTypeName )
	except:
		sys.stderr.write( "Failed to unregister node: %s\n" % kPluginTypeName )
		raise