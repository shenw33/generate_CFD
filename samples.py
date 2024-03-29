import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
# from get_solution import get_solution
# from .cavity_solver import solve_flow # only in colab!!!!
from cavity_solver import solve_flow
import matplotlib.pyplot as plt

def get_training_data(batch_size, domain_size, warm_start = False, u_h = None, v_h = None, p_h = None):
    "Get weakly supervised learning data"
    n_channels = 3
    img = torch.zeros(batch_size,n_channels,domain_size,domain_size)
    U = torch.zeros(batch_size,1,domain_size,domain_size)
    V = torch.zeros(batch_size,1,domain_size,domain_size)

    # u, v, p = solve_flow(100, domain_size, domain_size, u, v, dt, dx, dy, p, u0=1.0)
    P = torch.zeros(batch_size,1,domain_size,domain_size)

    # UPDATE @0109:
    u0 = np.random.uniform(0, 0.5)
    v0 = np.random.uniform(0, 0.5)
#     blank_part = np.random.randint(3,domain_size-1) 
    blank_part = domain_size + 1
    
    
    # Set the BC @ X = 0!
    U[:,:,0,0:blank_part - 1] = u0
    V[:,:,0,0:blank_part - 1] = v0

    U[:,:,1:-1,1:-1] = 0.001
    V[:,:,1:-1,1:-1] = 0.001
    P[:,:,0:-1,:] = 0.001 

    # V[:,:,1:-1,1:-1] = 0.1
    # P[:,:,1:-1,1:-1] = 0.1
    # geometry = torch.ones(batch_size,1,domain_size,domain_size)
    # d = 4
    # center = np.random.randint(d + 2, domain_size - d)
    # geometry[:,0,center-d:center+d, center-d:center + d] = 0
    img[:,0:1,:,:] = U # Channel 0
    img[:,1:2,:,:] = V # Channel 1
    img[:,2:3,:,:] = P # Channel 2

    if warm_start:

        # ROUGH WARM
        L = 1 # dimensionless LX / LX
        H = 1 # dimensionless LY / LX
        dx = L / (domain_size - 1)
        dy = H / (domain_size - 1)
        CFL = 0.04
        dt = CFL * min(dx , dy)
        RE = 20
        u = np.zeros((domain_size, domain_size))
        v = np.zeros((domain_size, domain_size))
        p = np.zeros((domain_size, domain_size))
        early_time_steps = 10
        u_h, v_h, p_h = solve_flow(early_time_steps, domain_size, domain_size, u, v, dt, dx, dy, p, u0=u0, v0=v0) # get rough results

        # Assign warm starting point
        img[:,0:1,1:-1,1:-1] = torch.from_numpy(u_h[1:-1,1:-1]).unsqueeze(0).unsqueeze(0) # Channel 0
        img[:,1:2,1:-1,1:-1] = torch.from_numpy(v_h[1:-1,1:-1]).unsqueeze(0).unsqueeze(0) # Channel 1
        img[:,2:3,0:-1, :] = torch.from_numpy(p_h[0:-1, :]).unsqueeze(0).unsqueeze(0) # Channel 2
    return img

def get_samples(size, u0, v0=0, dtype=torch.FloatTensor, warm_start = False, u_h = None, v_h = None, p_h = None):
    
    "u_h, v_h, p_h is the choice of exact solution for warm starting the model"

    L = 1 # dimensionless LX / LX
    H = 1 # dimensionless LY / LX
    dx = L / (size - 1)
    dy = H / (size - 1)
    CFL = 0.04
    dt = CFL * min(dx , dy)
    RE = 20
    u = np.zeros((size, size))
    # Set BC
    u[0, :] = u0
    v = np.zeros((size, size))
    v[0, :] = v0
    p = np.zeros((size, size))

#     blank_part = size / 2
#     u0_vector = np.zeros((1,size))
#     u0_vector[0, 0:blank_part - 1] = u0  

    u_sol, v_sol, p_sol = solve_flow(10000, size, size, u, v, dt, dx, dy, p, u0=u0, v0=v0) # Get the solution from u_0 = u0
    
#     solution = get_solution(T, isNeum).cpu().detach().numpy()[0,0,:,:] # solution in 2D, while T in 4D
    if warm_start:
#         early_time_steps = 50
#         u, v, p = solve_flow(early_time_steps, size, size, u, v, dt, dx, dy, p, u0, RE)
        u[1:-1,1:-1] = np.copy( u_h[1:-1, 1:-1] )
        v[1:-1,1:-1] = np.copy( v_h[1:-1, 1:-1] )
        p[0:-1,:] = np.copy( p_h[0:-1, :] )
    else:
        u[1:-1,1:-1] = 0.001
        v[1:-1,1:-1] = 0.001
        p[0:-1,:] = 0.001 
    U = torch.from_numpy(u).unsqueeze(0).unsqueeze(0).type(dtype)
    V = torch.from_numpy(v).unsqueeze(0).unsqueeze(0).type(dtype)
    P = torch.from_numpy(p).unsqueeze(0).unsqueeze(0).type(dtype)
    S_ini = torch.cat([U, V, P], dim=1)
    s_sol = (u_sol, v_sol, p_sol)
    return S_ini, s_sol


def show_samples(sol_u, sol_v, sol_p, pred4D, epoch, dirName):
    "f_0 solution" # 3 channels
    "n_0 prediction"
    UMAX, UMIN = 0.5, -0.5
    VMAX, VMIN = 1.0, -0.25
    PMAX, PMIN = 6.5, -2.5

    # size = f_0.shape[0]
    # n_0 = n_0.cpu().detach().numpy()[0,0,:,:]
    u_pred = pred4D.cpu().detach().numpy()[0,0,:,:]
    v_pred = pred4D.cpu().detach().numpy()[0,1,:,:]
    p_pred = pred4D.cpu().detach().numpy()[0,2,:,:]

    #     f_0[size//2 - d + 1 : size//2 + d - 1, size//2 -d + 1 : size//2 + d - 1] = np.nan
    #     n_0[0,0, size//2 -d + 1 : size//2 + d - 1, size//2 -d + 1 : size//2 + d - 1] = np.nan
    fig, axes = plt.subplots(2,3,figsize=(12,6))
    axes[0,0].imshow(u_pred, vmax=UMAX, vmin=UMIN, cmap=plt.cm.inferno)
    axes[0,0].set_title("X-Velocity") 
    axes[0,1].imshow(v_pred, vmax=VMAX, vmin=VMIN, cmap=plt.cm.inferno)
    axes[0,1].set_title("Y-Velocity") 
    axes[0,2].imshow(p_pred, vmax=PMAX, vmin=PMIN, cmap=plt.cm.inferno)
    axes[0,2].set_title("Pressure") 

    axes[1,0].imshow(sol_u, vmax=UMAX, vmin=UMIN, cmap=plt.cm.inferno)
    axes[1,1].imshow(sol_v, vmax=VMAX, vmin=VMIN, cmap=plt.cm.inferno)
    axes[1,2].imshow(sol_p, vmax=PMAX, vmin=PMIN, cmap=plt.cm.inferno)

    fig.text(0.06, 0.7, 'Model Generation', fontsize=14, ha='center', va='center', rotation='vertical')
    fig.text(0.06, 0.3, 'FDM Solution', fontsize=14, ha='center', va='center', rotation='vertical')
    fig.suptitle('Generation at epoch # {}'.format(epoch), fontsize=16)
    fig.savefig('{}/predict_epoch{}.png'.format(dirName, epoch))
    plt.close()

def RMSELoss(yhat, y, dtype=torch.FloatTensor):
    rmse = torch.sqrt(torch.mean((yhat.type(dtype) - y.type(dtype))**2))
    return float(rmse)
    
def saveRMS(err_list):
    plt.figure()
    plt.plot(range(1,len(err_list) + 1), err_list)
    plt.ylabel('RMS error')
    plt.xlabel('epochs')
    plt.savefig('err_list.png')
    plt.close()