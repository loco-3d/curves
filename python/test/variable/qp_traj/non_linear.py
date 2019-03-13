
import cvxpy as cp
from numpy.random import randn
from numpy import eye, ones, zeros, array
import numpy as np
from scipy.optimize import minimize

from  cord_methods import *
from  plot_cord import *

from straight_lines import solve_straight_lines, add_acc, bezierFromVal

eps =0.000001

degree = 5
n = degree
nvars = degree+1
dim = 2
rdim = 2

jmp = nvars * dim


def boundIneq():
    v = ones(4)*1.; #v[:-3] = -v[3:]
    V = zeros((4,2)); 
    V[:2,:] = identity(2); 
    V[2:,:] =-identity(2); 
    return (V, v)


def get_x(x,i,xid):
    return x[i*jmp + xid*dim:i*jmp+(xid+1)*dim]

def get_ti(x,i):
    return x[i*jmp+nvars*dim + i]

def c0(x, i):
    return get_x(x,i,0)
    
def c5(x, i):
    return get_x(x,i,5)
    
def c1(x, i):    
    return c0(x, i) + get_x(x,i,1) * get_ti(x,i)    
    
def c4(x, i):
    return c5(x, i) - get_x(x,i,4) * get_ti(x,i)
    
def c2(x, i):
    return get_x(x,i,2) * get_ti(x,i) * get_ti(x,i) + 2*c1(x, i) - c0(x, i)
    
def c3(x, i):
    return get_x(x,i,3) * get_ti(x,i) * get_ti(x,i) + 2*c4(x, i) - c5(x, i)
    
cjs = [c0,c1,c2,c3,c4,c5]
    
def cj(x,j, i):
    return cjs[j](x,i)
    
def dcj(x,j,i):
    return n / get_ti(x,i) * (cj(x,j+1, i) - cj(x,j, i))
    
def ddcj(x,j,i):
    return (n-1) / get_ti(x,i) * (dcj(x,j+1, i) - dcj(x, j, i))
#~ def position_constraints(Pis):



def position_cons(P,p,i):
    
    def evaluate(j, i):
        def ev(x):
            #~ print "cons", j,  (p - P[:,:rdim].dot(cj(x,j,i)) >= 0) .all()
            return p - P[:,:rdim].dot(cj(x,j,i))
        #~ return lambda x: p - P[:,:rdim].dot(cj(x,j,i))
        return ev
        
    def evaljac(j, i):
        def ev(x):            
            res = zeros((P.shape[0],x.shape[0]))
            res [:,i*jmp + j*dim:i*jmp+(j+1)*dim] = P[:,:rdim]
            return res
        #~ return lambda x: p - P[:,:rdim].dot(cj(x,j,i))
        return ev
    
    return [ 
              {'type': 'ineq',
              #~ 'fun' : lambda x:  p - P[:,:rdim].dot(cj(x,j,i)) ,} #contraint is >0 
              'fun' : evaluate(j, i) , #contraint is >0 
              #~ 'jac' : evaljac(j, i) , #contraint is >0 
               } #contraint is >0 
              for j in range(nvars)
        ]
        
def vel_cons(V,v,i):
    
    def evaluate(j, i):
        #~ def ev(x):
            #~ print "consV", (v - V.dot(dcj(x,j,i))>=0).all()
            #~ return v - V.dot(dcj(x,j,i))
        return lambda x: v - V.dot(dcj(x,j,i))
        #~ return ev
        
    return [ 
              {'type': 'ineq',
              'fun' : evaluate(j, i) ,} #contraint is >0 
              for j in range(nvars-1)
        ]
    
def t_pos_cons(nphases):
    return [{'type': 'ineq',
              'fun' : lambda x:  x[-nphases:] - ones(nphases)*0.0001}]
    
def flatlist(l):
    return [item for sublist in l for item in sublist]
        
def all_position_constraints(Pis, nphases):
    return flatlist ([position_cons(Pis[i][0],Pis[i][1],i) for i in range(nphases)])
    
def all_velocity_constraints(Vv, nphases):
    l = [vel_cons(Vv[0],Vv[1],i) for i in range(nphases)]
    return flatlist (l)
    
def cn_continuity_constraints(i,m):    
    def eq(x):
        return get_x(x,i-1,nvars-1-m) - get_x(x,i,m)
        
    return   {'type': 'eq',
              'fun' : eq ,} #contraint is >0     
    
def all_cn_continuity_constraint(nphases):
    return [cn_continuity_constraints(i,0) for i in range(1,nphases)]
    + [cn_continuity_constraints(i,1) for i in range(1,nphases)] + [cn_continuity_constraints(i,2) for i in range(1,nphases)]
    
def start_state_constraint(start):
    def eqs(x):
        #~ print "start", start 
        #~ print "start", get_x(x,0,0) - start[:rdim] 
        return get_x(x,0,0) - start[:rdim]
    print "init"
    return   [{'type': 'eq',
              'fun' : eqs ,} ]
              
def end_state_constraint(nphase, end):
    def eqe(x):
        return get_x(x,nphase-1,nvars-1) - end[:rdim]
        
    return   [{'type': 'eq',
              'fun' : eqe ,} ]
    
    
def all_constraints(Pis,nphases, start, end):
    print "heo"
    Vv = boundIneq()
    return all_position_constraints(Pis,nphases) + all_velocity_constraints(Vv, nphases) + t_pos_cons(nphases)  + all_cn_continuity_constraint(nphases) + start_state_constraint(start) + end_state_constraint(nphases,end)
    #~ return all_position_constraints(Pis,nphases) + t_pos_cons(nphases)
    #~ return all_velocity_constraints(Vv, nphases) + t_pos_cons(nphases)
    
        
def objective(nphases):
    #~ obj = ones(nvars * dim * nphases + nphases) #times at the end
    obj = zeros(nvars * dim * nphases + nphases) #times at the end
    obj [-nphases:] = ones(nphases)
    def fun(x):
        return obj.dot(x)
    return fun
    
def bounds(nphases):
    return[(0,None) for _ in range(nvars * dim * nphases)] + [(0.0001,None) for _ in range(nphases)]    
 
 
def acc(xs,ts,nphase, V):
    xis_rec = []
    for i in range(nphase):
        xis = xs[i*4:i*4+4]
        xis = [xis[0], zeros(dim), zeros(dim)] + [zeros(dim), zeros(dim), xis[-1]]
        xis_rec = xis_rec + xis
    return xis_rec

def init_guess(pDef,Pis,nphases, plot=True):
    V = boundIneq()
    x_start = pDef.start.reshape((-1,))
    x_end = pDef.end.reshape((-1,))
    prob, xis, tis = solve_straight_lines(Pis[:], V, x_start=x_start, x_end=x_end)    
    
    #~ print "stragiht ", xis
    if plot:
        for i in range(len(tis)):
            ti = abs(tis[i][0])
            b = bezierFromVal(xis[i*4:i*4+4], abs(ti))
            plotBezier(b, colors[i], label = None, linewidth = 3.0)
            plotControlPoints(b, colors[i],linewidth=2)
    
    xis = acc(xis,tis,nphases,V)
    #~ print "acc ", xis
    l = flatlist([el.tolist() for el in xis]) + tis
    return array(l).reshape((-1,))
    
    

    
    
if __name__ == '__main__':
    
        
    def one(nphases=2):
        plt.close()
        pDef, Pis = genProblemDef(6,nphases)
        x_start = pDef.start.reshape((-1,))
        x_end = pDef.end.reshape((-1,))

        x0 = init_guess(pDef, Pis,nphases)   
        
        #~ print "bounds", bounds(nphases)
        #~ print "bounds", (x0 >= bounds(nphases)[0]).all()
        #~ print "bounds", (x0 <= bounds(nphases)[1]).all()
        
        #~ print "x0", x0
        
        #~ print "c0", c0(x0, 0)
        #~ print "c1", c1(x0, 0)
        #~ print "c2", c2(x0, 0)
        #~ print "c3", c3(x0, 0)
        #~ print "c4", c4(x0, 0)
        #~ print "c5", c5(x0, 0)
        #~ print "c0", c0(x0, 1)
        #~ print "c1", c1(x0, 1)
        #~ print "c2", c2(x0, 1)
        #~ print "c3", c3(x0, 1)
        #~ print "c4", c4(x0, 1)
        #~ print "c5", c5(x0, 1)
        
        #~ print "bounds", bounds(nphases)[0].shape
        
        #~ plt.show()
        res = minimize(objective(nphases), x0, method='SLSQP',
               constraints=all_constraints(Pis,nphases,x_start,x_end), options={'ftol': 1e-5, 'disp': True},
               bounds=bounds(nphases)
               )
               
       
        wp1 = array([array(cj(res.x,j, 0).tolist() + [0.]) for j in range(6)]).T
        wp2 = array([array(cj(res.x,j, 1).tolist() + [0.]) for j in range(6)]).T
        b1 = bezier(wp1)
        b2 = bezier(wp2)
        plotBezier(b1, "r", label = None, linewidth = 2.0)
        plotControlPoints(b1, "r",linewidth=2)
        plotBezier(b2, "b", label = None, linewidth = 2.0)
        plotControlPoints(b2, "b",linewidth=2)
        plt.show()
        return res
        
    res = one()
    #now plot
