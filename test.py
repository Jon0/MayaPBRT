import math, sys

import maya.cmds as cmds

import maya.OpenMaya as OpenMaya
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

					if (objectType ==  "kTransform"):
						self.currentTransform = OpenMaya.MFnTransform( object )
						#fileHandle.write( "# .. "+str(matrix)+"\n" )

					# camera position and direction
					if (objectType ==  "kCamera" and objectName == "perspShape"):	
						dnFn = OpenMaya.MFnCamera( object )
						cameraStr += self.cameraStr(dnFn)

				except:
					raise
				iterator.next()

			fileHandle.write("\n\n# RENDER\n")
			fileHandle.write("Film \"image\" \"string filename\" [\"test.exr\"]")
			fileHandle.write("\"integer xresolution\" [960] \"integer yresolution\" [540]\n")
			

			fileHandle.write("Renderer \"sampler\"\n\n")

			fileHandle.write( cameraStr )
			#fileHandle.write("LookAt 0 .2 .2    -.02 .1 0  0 1 0\n")
			

			fileHandle.write("WorldBegin\n\n")

			fileHandle.write( lightStr )

			fileHandle.write( meshStr )
			fileHandle.write("WorldEnd\n")
			fileHandle.close()
		except:
			sys.stderr.write( "Failed to write file information\n")
			raise

	def defaultExtension(self):
		return "pbrt"

	def lightStr(self, dnFn):
		# float intensity
		intensity = dnFn.intensity() * 20
		rgb = [intensity] * 3
		position = self.currentTransform.transformation().getTranslation(OpenMaya.MSpace.kWorld)

		lStr = "# LIGHT\n"
		lStr += "AttributeBegin\n"
		lStr += "LightSource \"point\" \"rgb I\" ["+str(rgb[0])+" "+str(rgb[1])+" "+str(rgb[2])+" "+"] "
		lStr += "\"point from\" ["+str( self.point3Str(position) )+"]\n"
		lStr += "AttributeEnd\n\n"

		return lStr;

	def cameraStr(self, dnFn):
		# "LookAt 0 .2 .2    -.02 .1 0  0 1 0\n"

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

		vertexArray = OpenMaya.MPointArray()
		dnFn.getPoints(vertexArray, OpenMaya.MSpace.kWorld)

		index_str = ""
		vert_str = ""
		normal_str = ""
		count = 0

		numpolys = dnFn.numPolygons()
		for p in range( 0, numpolys ):
			trisInPoly = triangleCounts[p]
			pbrtshape += "# tcounts = "+str(trisInPoly)+"\n"

			for tri in range( 0, triangleCounts[p] ):

				# get 3 verts for the triangle
				util = OpenMaya.MScriptUtil()
  				util.createFromList([0] * 3, 3)
  				ptr = util.asIntPtr()
				dnFn.getPolygonTriangleVertices(p, tri, ptr)

				# each vert in the triangle
				for vv in range( 0, 3 ):
					vertid = OpenMaya.MScriptUtil.getIntArrayItem(ptr, vv)
					vnorm = OpenMaya.MVector()
					#vpos = OpenMaya.MPoint()

					# get the points and normals in world space
					# kWorld applies all transformations in the dag path
					dnFn.getFaceVertexNormal(p, vertid, vnorm, OpenMaya.MSpace.kWorld)
					#dnFn.getPoint(vertid, vpos, OpenMaya.MSpace.kWorld)
					vpos = vertexArray[vertid]


					index_str += str(count) + " "
					vert_str += self.point3Str(vpos)
					normal_str += self.point3Str(vnorm)
					pbrtshape += "# ii === "+str(vertid)+" "+str(triangleVertices[count])+"\n"
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

		# return string
		return pbrtshape;

	def point3Str(self, vectorIn):
		vec = ""
		vec += str(-vectorIn[0]) + " "
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