# Note 1: I am using the latest simnpleoctree.py in the makehuman svn
import math
import simpleoctree
from aljabr import *

def drawLine(point1,point2,name):
    coords=[point1, point2]  
    faces= [[0,1]]
    me = Mesh.New()         # create a new mesh
    me.verts.extend(coords)          # add vertices to mesh
    me.faces.extend(faces)           # add faces to the mesh (also adds edges)
    scn = Scene.GetCurrent() #get current scene
    scn.objects.new(me,name)
    Blender.Redraw()
    
#Normal direction is from point1 to point2!
# i is an integer corresponding to the vertex order of the mesh
def drawNormal(i, obj, size,name):
    mesh = obj.getData()
    normal = mesh.verts[i].no
    point1 = local2World(mesh.verts[i].co,obj.getMatrix())
    point2 = vadd(point1, vmul(normal,size))
    drawLine(point1,point2,name)

def local2World(vec, matrix):
    x, y, z = vec
    xloc, yloc, zloc = matrix[3][0], matrix[3][1], matrix[3][2]
    return  [x*matrix[0][0] + y*matrix[1][0] + z*matrix[2][0] + xloc,\
            x*matrix[0][1] + y*matrix[1][1] + z*matrix[2][1] + yloc,\
            x*matrix[0][2] + y*matrix[1][2] + z*matrix[2][2] + zloc]

def world2Local(vec, matrix):
    x, y, z = vec
    xloc, yloc, zloc = matrix[3][0], matrix[3][1], matrix[3][2]
    return  [(x-xloc)*matrix[0][0] + (y-yloc)*matrix[0][1] + (z-zloc)*matrix[0][2],\
            (x-xloc)*matrix[1][0] + (y-yloc)*matrix[1][1] + (z-zloc)*matrix[1][2],\
            (x-xloc)*matrix[2][0] + (y-yloc)*matrix[2][1] + (z-zloc)*matrix[2][2]]
 
def getTangent(point,i,obj,size,isNurb=False, res=0.08): #default Octree Resolution is set to 0.08
    l = 1.5*res*math.sqrt(3.0) #longest distance of an octree smallest cube
    if (size<l) : l=size
    size= size - l #josenow
    mesh = obj.getData()
    L2 = local2World(mesh.verts[i].co,obj.getMatrix())
    vec1 = vsub(point,L2)
    normal = mesh.verts[i].no
    #if math.abs(diffang(vec1,normal))
    scalar = vdot(normal,vec1)
    point2=[]
    if isNurb and (not scalar == 0) and math.fabs(math.acos(scalar/vlen(vec1))) > math.pi/2 : 
    #For nurbs.. is angle of incidence obtuse? if so deflect through the same direction as incident from point
        point2 = vmul(vec1,-res/vlen(vec1))
        point2= vadd(L2,point2)
        print "point2 is: ", point2
        print "Deflection is done through incidence"
    else:
        #YES! then try to deflect through the tangent space 
        tangent = vsub(vec1,vmul(normal,scalar))
        N= vlen(tangent)
        if not N==0: 
            tangent = vmul(tangent,-l/N)
            point2 = vadd(L2, tangent)
            point2 = vadd(point2,vmul(normal,res))
            #return[L2,point2]
        else: #collision and normal lines are parallel
            print "Collision and normal lines are parallel"
            tangent = [normal[0],-normal[2],normal[1]] #arbitrary rotation of 90deg.. choose x-axis rotation!
            tangent = vmul(tangent, l)
            point2 = vadd(L2,tangent)
    if (size<=0): return [L2,point2]
    else: return [L2, point2, vadd(point2,vmul(normal,size))]
 
#check if an unordered interval (i.e. we can have [a,b] with a>=b) is in an ordered interval (i.e. [a,b] has always a<=b)
def unordInOrd(unord,ord):
    if unord[0] <= unord[1]:
        return unord[0]<=ord[1] and ord[0]<=unord[1]
    else:
        return unord[1]<=ord[1] and ord[0]<=unord[0]

#checks if 2 ordered interval in real numbers intersect
def intIntersects(int1,int2):
    return int1[0]<=int2[1] and int2[0]<=int1[1]
        
#checks if line crosses cube! 
#line consists of two vertices
def lineInCube(line,cube):
    returnValue = False
    x = [line[0][0],line[1][0]]
    #Projection on 1dim, x-axis:
    if unordInOrd(x,[cube[0][0],cube[1][0]]):
        if x[0]<=x[1]:
            if x[0]<cube[0][0]: x[0] = cube[0][0]
            if x[1]>cube[1][0]: x[1] = cube[1][0]
        else:
            if x[1]<cube[0][0]: x[1] = cube[0][0]
            if x[0]>cube[1][0]: x[0] = cube[1][0]
        #Projection on 2dimensions, x and y-axes
        y=[[],[]]
        t1,t2=[],[]
        if not line[1][0]==line[0][0]:
            t1=(x[0]-line[0][0])/(line[1][0]-line[0][0]) #basic homlogical algebra
            y[0] = line[0][1]*(1-t1)+line[1][1]*t1 #intersection between line and cube in y-axis
            t2=(x[1]-line[0][0])/(line[1][0]-line[0][0]) 
            y[1] = line[0][1]*(1-t2)+line[1][1]*t2 
        else: #line is vertical, i.e. x remains constant!
            y[0] = line[0][1]
            y[1] = line[1][1]
            t1,t2 =0,1
        if unordInOrd(y,[cube[0][1],cube[1][1]]):
            #Entire 3D
            z=[[],[]]
            z[0] = line[0][2]*(1-t1)+line[1][2]*t1 #intersection between line and cube in z-axis
            z[1] = line[0][2]*(1-t2)+line[1][2]*t2
            returnValue = unordInOrd(z,[cube[0][2],cube[1][2]])
    return returnValue

def lineInColoredLeaf(line, root): #root is of type SimpleOctreeVolume found in simpleoctree.py
    cube = [root.bounds[0], root.bounds[6]] #take the two corners that fully defines a cube
    if not lineInCube(line,cube):
        return False
    elif len(root.children) == 0: #is it a leaf?
        if len(root.verts) == 0: # is it an empty leaf?
            return False
        else: 
            #print "cube where line is located is in: ", cube
            #print "line is : ", line
            #drawLine(line[0],line[1],"l")
            return True #line passes through a colored leaf!
    else:
        returnValue = False
        i=0
        while returnValue == False and i<len(root.children):
            returnValue = lineInColoredLeaf(line,root.children[i])
            i=i+1 #recursive search through children and ask if line passes a colored leaf
    return returnValue
    
#line consist of two vertices in world coordinates, line is in general two subsequent control point of a curve
#i is the ith vertex of object by which line must be deflected
#isNurb asks whether line is subsequent controlPoint of a nurb, if yes then the algorithm is improved so deflection regards the actualy 
#curve and not the line connecting controlpoints
#line consist of two vertices in world coordinates, line is in general two subsequent control point of a curve
#i is the ith vertex of object by which line must be deflected
#isNurb asks whether line is subsequent controlPoint of a nurb, if yes then the algorithm is improved so deflection regards the actualy 
#curve and not the line connecting controlpoints
def deflect(line,obj,gravity,isNurb=True): #assume gravity is negative y-direction!
    G=[0,-1,0] #vector direction of gravity
    mesh = obj.getData()
    #dist = distance(line[0],mesh.verts[0].co)
    dist=() #infinity in python
    near = []
    for j in range(0,len(mesh.verts)):
        if [mesh.verts[j].co[0],mesh.verts[j].co[1],mesh.verts[j].co[2]]==line[1]: 
            return 0 #0 means do not change the curve
            print "line[1] and mesh verts match"
        if (gravity and mesh.verts[j].co[1] < line[0][1]) or not gravity: #assume G=[0,-1,0]
            distTemp = vdist(line[0],mesh.verts[j].co)
            if distTemp < dist:
                dist = distTemp
                near = j
    if near==[]:
        #print "near was []. this usually SHOULD NOT happen!"
        return 0
    else:
        size = vdist(mesh.verts[near].co,line[1])
    #get unit normal
    if size > 0.0001: #TODO add minimal unit
        if not gravity:
            return getTangent(line[0],near,obj,size,isNurb)
        else: 
            point = [mesh.verts[near].co[0],mesh.verts[near].co[1],mesh.verts[near].co[2]]
            point = vsub(point,G)
            return getTangent(point,near,obj,size,isNurb)

#res = resolution of minsize of octree
#i is the index of curve where collision should start!
def collision(curve,obj,res,i=1,gravity=True):
    #newcurve = curve[:] #make deep copy of curve
    mesh= obj.getData() #NOTICE : we assume obj is centered at [0,0,0]
    mat = obj.getMatrix()
    octree = simpleoctree.SimpleOctree(mesh.verts,res)
    N=len(curve)
    while i<N: 
        point1 = world2Local(curve[i-1],mat)
        point2 = world2Local(curve[i],mat)
        print "i, N : ",i,N #todelete
        if lineInColoredLeaf([point1,point2],octree.root):
            if i==N-1:
                tangent = deflect([curve[i-1],curve[i]],obj,gravity)
            else:
                tangent = deflect([curve[i-1],curve[i],curve[i+1]],obj,gravity)
            n=1
            if not tangent ==0:
                if not curve[i-1]==tangent[0]: #TODO in case after Tangent deflection we passthrough a second part of the body!
                    if len(tangent) ==3: n=2
                    delta = vsub(tangent[n],curve[i])
                    for k in range(0,n):
                        curve.insert(i,tangent[n-1-k])
                    for j in range(i+n,len(curve)):
                        curve[j] = vadd(curve[j],delta)
                    N=N+n
            i=i+n
        i=i+1
