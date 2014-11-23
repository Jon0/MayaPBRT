import math, sys
import subprocess

import maya.mel as mel
import maya.cmds as cmds

import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMayaAnim as OpenMayaAnim
import maya.OpenMayaMPx as OpenMayaMPx

kPluginTypeName = "pbrtExport"

#pbrtExportId = OpenMaya.MTypeId(0x8702)

def materialStr(obj):
	mat = OpenMaya.MFnLambertShader( obj )
	mStr = "# MATERIAL\n"

	#parr = OpenMaya.MPlugArray()
	#mat.getConnections(parr)
	#for x in range( 0, parr.length() ):
	#	mStr += parr[x].name() + " "

	c = mat.color()
	cStr = str(c[0])+" "+str(c[1])+" "+str(c[2])+" "

	mStr += "Material \"matte\" \"rgb Kd\" ["+cStr+"]"
	mStr += "\n"
	return mStr


# Node definition
class pbrtExport(OpenMayaMPx.MPxFileTranslator):
	# class variables
	#angle = OpenMaya.MObject()
	#filename = OpenMaya.MObject()
	currentTransform = OpenMaya.MFnTransform()

	# constructor
	def __init__(self):
		OpenMayaMPx.MPxFileTranslator.__init__(self)

	def haveReadMethod(self):
		return False

	def haveWriteMethod(self): 
		return True;

	def writer( self, fileObject, optionString, accessMode ):
		meshStr = ""
		lightStr = ""
		cameraStr = ""
		try:
			fullName = fileObject.fullName()
			fileHandle = open(fullName,"w")

			# find material
			mIter = OpenMaya.MItDependencyNodes()
			while not mIter.isDone():
				obj = mIter.thisNode()
				objectType = obj.apiTypeStr()
				#if (objectType ==  "kLambert"):
				#	fileHandle.write("# "+materialStr(obj)+"\n")
				mIter.next()

			# iterate over dag nodes
			iterator = OpenMaya.MItDag()
			while not iterator.isDone():
				try:
					object = OpenMaya.MDagPath()
					iterator.getPath(object)
					objectType = iterator.currentItem().apiTypeStr()

					# MFnDependencyNode
					dNode = OpenMaya.MFnDagNode( object )
					objectName = dNode.name()
					fileHandle.write("# "+objectType+" -> "+objectName+"\n")

					# mesh geometry
					if (objectType ==  "kMesh"):
						meshStr += self.meshStr(object)

					# point light source
					if (objectType ==  "kPointLight"):
						dnFn = OpenMaya.MFnPointLight( object )
						lightStr += self.lightStr(dnFn)

					# spot light source
					if (objectType ==  "kSpotLight"):
						dnFn = OpenMaya.MFnSpotLight( object )
						lightStr += self.spotlightStr(dnFn)

					# directional light source
					if (objectType ==  "kDirectionalLight"):
						dnFn = OpenMaya.MFnDirectionalLight( object )
						lightStr += self.dirlightStr(dnFn)

					# area source
					if (objectType ==  "kAreaLight"):
						dnFn = OpenMaya.MFnAreaLight( object )
						lightStr += self.areaLightStr(dnFn)

					if (objectType ==  "kTransform"):
						self.currentTransform = OpenMaya.MFnTransform( object )
						#fileHandle.write( "# .. "+str(matrix)+"\n" )

				except:
					raise
				iterator.next()

			# camera position and direction
			activeView = OpenMayaUI.M3dView.active3dView()
			object = OpenMaya.MDagPath()
			activeView.getCamera(object)
			dnFn = OpenMaya.MFnCamera( object )
			cameraStr += self.cameraStr(dnFn)


			fileHandle.write("\n\n# RENDER\n")
			
			fileHandle.write("Scale -1 1 1\n")

			fileHandle.write("Film \"image\" \"string filename\" [\"test.exr\"]")
			fileHandle.write("\"integer xresolution\" [960] \"integer yresolution\" [540]\n")
			
			fileHandle.write("Renderer \"sampler\"\n\n")
			fileHandle.write( cameraStr )

			fileHandle.write("WorldBegin\n\n")
			fileHandle.write( lightStr )
			fileHandle.write( meshStr )
			fileHandle.write("WorldEnd\n")
			fileHandle.close()

			#cb = mel.eval("$temp=$display_output")
			#sys.stderr.write( "cb = %s\n" % cb)

			#p = subprocess.Popen('pbrt test.pbrt', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			#for line in p.stdout.readlines():
			#	print line
			#retval = p.wait()

			#p = subprocess.Popen('exrdisplay test.exr', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			#for line in p.stdout.readlines():
			#	print line
			#retval = p.wait()

		except:
			sys.stderr.write( "Failed to write file information\n")
			raise

	def defaultExtension(self):
		return "pbrt"

	def lightStr(self, dnFn):
		# float intensity
		intensity = dnFn.intensity()
		rgb = [intensity] * 3
		colour = dnFn.color()
		for x in range( 0, 3 ):
			rgb[x] = rgb[x] * colour[x]


		position = self.currentTransform.transformation().getTranslation(OpenMaya.MSpace.kWorld)

		lStr = "# POINT LIGHT\n"
		lStr += "AttributeBegin\n"
		lStr += "LightSource \"point\" \"rgb I\" ["+str(rgb[0])+" "+str(rgb[1])+" "+str(rgb[2])+" "+"] "
		lStr += "\"point from\" ["+str( self.point3Str(position) )+"]\n"
		lStr += "AttributeEnd\n\n"
		return lStr

	def spotlightStr(self, dnFn):
		# float intensity
		intensity = dnFn.intensity()
		rgb = [intensity] * 3
		colour = dnFn.color()
		for x in range( 0, 3 ):
			rgb[x] = rgb[x] * colour[x]

		# position and direction
		transform = self.currentTransform.transformation().asMatrix()

		lStr = "# SPOT LIGHT\n"
		lStr += "AttributeBegin\n"
		lStr += "Transform ["
		for x in range( 0, 4 ):
			for y in range( 0, 4 ): 
				lStr += str(transform(x, y)) + " "
		lStr += "]\n"

		lStr += "LightSource \"spot\" \"rgb I\" ["+str(rgb[0])+" "+str(rgb[1])+" "+str(rgb[2])+" "+"] "
		lStr += "\"point from\" [0 0 0]\n"
		lStr += "\"point to\" [0 0 -1]\n"
		lStr += "\"float coneangle\" ["+str( math.degrees(dnFn.coneAngle() / 2) )+"]\n"
		lStr += "\"float conedeltaangle\" ["+str( math.degrees(dnFn.penumbraAngle() / 2) )+"]\n"
		lStr += "AttributeEnd\n\n"
		return lStr

	def dirlightStr(self, dnFn):
		# float intensity
		intensity = dnFn.intensity()
		rgb = [intensity] * 3
		colour = dnFn.color()
		for x in range( 0, 3 ):
			rgb[x] = rgb[x] * colour[x]
		direction = dnFn.lightDirection(0, OpenMaya.MSpace.kWorld)

		lStr = "# DIRECTIONAL LIGHT\n"
		lStr += "AttributeBegin\n"
		lStr += "LightSource \"distant\" \"rgb I\" ["+str(rgb[0])+" "+str(rgb[1])+" "+str(rgb[2])+" "+"] "
		lStr += "\"point from\" ["+str( self.point3Str(position) )+"]\n"
		lStr += "AttributeEnd\n\n"
		return lStr

	def areaLightStr(self, dnFn):
		lStr = "# AREA LIGHT\n"
		lStr += "AttributeBegin\n"
		lStr += "AreaLightSource \"diffuse\" \"rgb L\" [ 10.5 10.5 10.5 ]\n"
		lStr += "Translate 0 10 0\n"
		lStr += "Shape \"sphere\" \"float radius\" [.25]\n"
		lStr += "AttributeEnd\n\n"
		return lStr


	def cameraStr(self, dnFn):
		camStr = "# CAMERA\n"
		camStr += "LookAt "

		#  * self.currentTransform
		eyePoint = dnFn.eyePoint(OpenMaya.MSpace.kWorld)
		eyeDirection = dnFn.viewDirection(OpenMaya.MSpace.kWorld)
		eyeUp = dnFn.upDirection(OpenMaya.MSpace.kWorld)

		camStr += self.point3Str(eyePoint)
		camStr += self.point3Str(eyeDirection)
		camStr += self.point3Str(eyeUp)
		camStr += "\n"

		if ( dnFn.isOrtho() ):
			camStr += "Camera \"orthographic\"\n\n"
		else:
			# convert to degrees
			fov = math.degrees( dnFn.horizontalFieldOfView() / 2 )
			camStr += "Camera \"perspective\" \"float fov\" ["+str(fov)+"]\n\n"
		return camStr;

	def meshStr(self, oIn):
		dnFn = OpenMaya.MFnMesh( oIn )

		pbrtshape = "# SHAPE\n"
		pbrtshape += "# verts = "+str(dnFn.numVertices())+" normal = "+str(dnFn.numNormals())+" poly = "+str(dnFn.numPolygons())+"\n"
		pbrtshape += "# fverts = "+str(dnFn.numFaceVertices())+"\n"


		shaders = OpenMaya.MObjectArray()
		indices = OpenMaya.MIntArray()
		ac = dnFn.getConnectedShaders(0, shaders, indices)
		for x in range( 0, shaders.length() ):
			if (shaders[x].apiTypeStr() == "kShadingEngine"):
				shd = OpenMaya.MFnDependencyNode(shaders[x])
				mat_plg = shd.findPlug("surfaceShader")
				material_conns = OpenMaya.MPlugArray()

				#get the connections to this attribute
				mat_plg.connectedTo(material_conns,True,False);

				for k in range( 0, material_conns.length() ):
					matObj = material_conns[k].node();

					if( matObj.apiTypeStr() == "kLambert" ):
						pbrtshape += materialStr(matObj)

		# triangles per poly
		triangleCounts = OpenMaya.MIntArray()
		triangleVertices = OpenMaya.MIntArray()
		dnFn.getTriangles(triangleCounts, triangleVertices)

		# normals per poly
		normalIdCounts = OpenMaya.MIntArray()
		normalIds = OpenMaya.MIntArray()
		dnFn.getNormalIds(normalIdCounts, normalIds)


		# size of vertexCount = number of polygons, vertexList contains verts for each poly -- getPolygonVertices gets same thing
		# verts per poly
		vertexCount = OpenMaya.MIntArray()
		vertexList = OpenMaya.MIntArray()
		dnFn.getVertices(vertexCount, vertexList)


		# get the points and normals in world space
		# kWorld applies all transformations in the dag path
		vertexArray = OpenMaya.MPointArray()
		dnFn.getPoints(vertexArray, OpenMaya.MSpace.kWorld)

		index_str = ""
		vert_str = ""
		normal_str = ""
		uv_str = ""
		count = 0

		#	find attributes of each vertex
		numpolys = dnFn.numPolygons()
		for p in range( 0, numpolys ):
			trisInPoly = triangleCounts[p]
			for tri in range( 0, triangleCounts[p] ):

				# get 3 verts for the triangle
				util = OpenMaya.MScriptUtil()
  				util.createFromList([0] * 3, 3)
  				ptr = util.asIntPtr()
				dnFn.getPolygonTriangleVertices(p, tri, ptr)

				# each vert in the triangle
				for vv in range( 0, 3 ):
					vertid = OpenMaya.MScriptUtil.getIntArrayItem(ptr, vv)
					vpos = vertexArray[vertid]

					vnorm = OpenMaya.MVector()
					dnFn.getFaceVertexNormal(p, vertid, vnorm, OpenMaya.MSpace.kWorld)
				
					# get uv
					uvPoint = OpenMaya.MScriptUtil()
					uvPoint.createFromList((0.0,0.0),2)
					uvPointPtr = uvPoint.asFloat2Ptr()
					dnFn.getUVAtPoint(vpos, uvPointPtr)

					index_str += str(count) + " "
					vert_str += self.point3Str(vpos)
					normal_str += self.point3Str(vnorm)
					uv_str += OpenMaya.MScriptUtil.getFloatArrayItem(uvPointPtr, 0)+" "
					uv_str += OpenMaya.MScriptUtil.getFloatArrayItem(uvPointPtr, 1)+" "
					count = count + 1

		pbrtshape += "Shape \"trianglemesh\" \"integer indices\" ["
		pbrtshape += index_str
		#for x in range( 0, triangleVertices.length() ):
		#	pbrtshape += str(triangleVertices[x]) + " "
		pbrtshape += "]\n"


		pbrtshape += "\"point P\" ["
		pbrtshape += vert_str
		#for x in range( 0, vertexArray.length() ):
		#	pbrtshape += self.point3Str(vertexArray[x]) + " "
		pbrtshape += "]\n"

		# number of normals greater or equal to vertices
		pbrtshape += "\"normal N\" ["
		pbrtshape += normal_str
		pbrtshape += "]\n\n"

		# uvs
		pbrtshape += "\"float uv\" ["
		pbrtshape += uv_str
		pbrtshape += "]\n\n"

		# return string
		return pbrtshape;

	def point3Str(self, vectorIn):
		vec = ""
		vec += str(vectorIn[0]) + " "
		vec += str(vectorIn[1]) + " "
		vec += str(vectorIn[2]) + " "
		return vec;

# creator
def translatorCreator():
	return OpenMayaMPx.asMPxPtr( pbrtExport() )
	
# initialize the script plug-in
def initializePlugin(mobject):
	mplugin = OpenMayaMPx.MFnPlugin(mobject)
	try:
		# gui
		#file = open("/u/students/remnanjona/git/MayaPBRT/exportOptions.mel", "r")
		mplugin.registerFileTranslator( kPluginTypeName, None, translatorCreator ) #, file.read()
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