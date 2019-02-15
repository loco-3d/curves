from hpp_spline import *
from numpy import matrix, array, zeros, ones, diag, cross
from numpy.linalg import norm

__EPS = 1e-6


from varBezier import varBezier
from qp_cord import *
from plot_cord import *


idxFile = 0
import string
import uuid; uuid.uuid4().hex.upper()[0:6]


######################## generate problems ########################

def genSplit(numCurves):
        splits = []
        lastval = np.random.uniform(0., 1.)
        for i in range(numCurves):
                splits += [lastval]
                lastval += np.random.uniform(0., 1.)
        return [el / lastval for el in splits[:-1]]        
                

def getRightMostLine(ptList):
        pt1 = array([0.,0.,0.])
        pt2 = array([0.,0.,0.])
        for pt in ptList:
                if pt[0] > pt1[0]:
                       pt1 =  pt
                elif pt[0] > pt2[0]:
                       pt2 =  pt
        if pt1[1] < pt2[1]:
                return [pt2,pt1]
        else:
                return [pt1,pt2]
                

#inequality constraint from line
def getLineFromSegment(line):
        a = line[0]; b = line[1]; c = a.copy() ; c[2] = 1.
        normal = cross((b-a),(c-a))
        normal /= norm(normal)
        # get inequality
        dire = b - a
        coeff = normal
        rhs = a.dot(normal)
        return (coeff, array([rhs]))
   
def genConstraintsPerPhase(pDef, numphases):        
        pData = setupControlPoints(pDef)
        vB = varBezier()
        bezVar = vB.fromBezier(pData.bezier())
        line_current = [array([1.,1.,0.]), array([0.,1.,0.])]
        dimExtra = 0
        for i in range(numphases):
                init_points = []
                if i == 0:
                        init_points = [bezVar.waypoints()[1][:3,0][:2]]
                if i == numphases-1:
                        init_points = [bezVar.waypoints()[1][-3:,-1][:2]]
                lines, ptList = genFromLine(line_current, 5, [[0,5],[0,5]],init_points)
                matineq0 = None; vecineq0 = None
                for line in lines:
                        (mat,vec) = getLineFromSegment(line)
                        (matineq0, vecineq0) = (concat(matineq0,mat), concatvec(vecineq0,vec))
                ineq  = (matineq0, vecineq0)
                pDef.addInequality(matineq0,vecineq0.reshape((-1,1)))
                line_current = getRightMostLine(ptList)
                plotPoly  (lines, colors[i])
######################## generate problems ########################

######################## solve a given problem ########################


colors=['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']



def genProblemDef(numvars = 3, numcurves= 4):
        valDep = array([[np.random.uniform(0., 1.), np.random.uniform(0.,5.), 0. ]]).T
        valEnd = array([[np.random.uniform(5., 10.), np.random.uniform(0.,5.), 0.]]).T
        pDef = problemDefinition()
        pDef.start = valDep
        pDef.end = valEnd
        pDef.degree = numvars + 1
        pDef.splits = array([genSplit(numcurves)]).T        
        genConstraintsPerPhase(pDef, numcurves+1) #load random inequality constraints
        return pDef

def __getbezVar(pDef): #for plotting only
        vB = varBezier()
        pData = setupControlPoints(pDef)
        return vB.fromBezier(pData.bezier())

def computeTrajectory(pDef, save, filename = uuid.uuid4().hex.upper()[0:6]):
        global idxFile
        global colors
        bezVar = __getbezVar(pDef)
        subs = bezVar.split(pDef.splits.reshape((-1)).tolist())
        ineq = generate_problem(pDef);
        #generate random constraints for each line
        line_current = [array([1.,1.,0.]), array([0.,1.,0.])]
        
        #qp vars
        P = accelerationcost(bezVar)[0]; P = P + identity(P.shape[0]) * 0.0001
        q = zeros(3*bezVar.bezier.nbWaypoints)
        q[-1] = -1
        G = zeros([2,q.shape[0]])
        h = zeros(2)
        G[0,-1] =  1 ; h[0]=1.
        G[1,-1] = -1 ; h[1]=0.
        G = vstack([G,ineq.A])
        h = concatvec(h,ineq.b.reshape((-1)))
        
        dimExtra = 0
        
        C = None; d = None
        try:
                res = quadprog_solve_qp(P, q, G=G, h=h, C=C, d=d)
                #plot bezier
                for i, bez in enumerate(subs):
                        color = colors[i]
                        test = bez.toBezier3(res[:])
                        plotBezier(test, color)
                if save:
                        plt.savefig(filename+str(idxFile))
                #plot subs control points
                for i, bez in enumerate(subs):
                        color = colors[i]
                        test = bez.toBezier3(res[:])
                        plotBezier(test, color)
                        plotControlPoints(test, color)
                if save:
                        plt.savefig("subcp"+filename+str(idxFile))
                final = bezVar.toBezier3(res[:])
                plotControlPoints(final, "black")
                if save:
                        plt.savefig("cp"+filename+str(idxFile))
                idxFile += 1
                if save:
                        plt.close()
                else:
                        plt.show()
                
                return final
        except ValueError:
                plt.close()
######################## solve a given problem ########################


#solve and gen problem
def gen(save = False):
        #~ testConstant = genBezierInput(20)
        #~ splits = genSplit(4)
        pDef = genProblemDef(20,4)
        return computeTrajectory(pDef, save)

res = None
for i in range(100):
        res = gen(False)
        #~ if res[0] != None:
                #~ break

