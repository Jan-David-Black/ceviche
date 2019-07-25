import unittest
import numpy as np
import matplotlib.pylab as plt
import autograd.numpy as npa

from scipy.optimize import minimize

import sys
sys.path.append('../ceviche')

from ceviche import fdfd_hz, jacobian
from ceviche.constants import *
from ceviche.utils import imarr

""" Optimize energy gain of dielectric particle accelerator """

# whether to plot things below
PLOT = False

# make parameters
wavelength = 2e-6                      # free space wavelength
omega = 2 * np.pi * C_0 / wavelength   # angular frequency
beta = .5                              # speed of electron / speed of light
dL = wavelength / 50.0                # grid size (m)

Nx, Ny = 400, int(beta * wavelength / dL)

eps_max = 2
eps_r = np.ones((Nx, Ny))
source = np.zeros((Nx, Ny))
source[30, :] = 10
npml = [20, 0]
spc = 100
gap = 20

# make design region
design_region = np.zeros((Nx, Ny))
design_region[spc:Nx//2-gap//2, :] = 1
design_region[Nx//2+gap//2:Nx-spc, :] = 1
eps_r[design_region == 1] = eps_max

# make the accelration probe
eta = np.zeros((Nx, Ny), dtype=np.complex128)
channel_ys = np.arange(Ny)
eta[Nx//2, :] = np.exp(1j * 2 * np.pi * channel_ys / Ny)

# plot the probe through channel
if PLOT:
    plt.plot(np.real(imarr(eta[Nx//2,:])), label='RE\{eta\}')
    plt.xlabel('position along channel (y)')
    plt.ylabel('eta (y)')
    plt.show()

# vacuum test, get normalization
F = fdfd_hz(omega, dL, eps_r, npml)
Ex, Ey, Hz = F.solve(source)
E_mag = np.sqrt(np.square(np.abs(Ex)) + np.square(np.abs(Ey)))
E0 = np.max(E_mag[spc:-spc, :])
print('E0 = {} V/m'.format(E0))

# plot the vacuum fields
if PLOT:
    plt.imshow(np.real(Ey) / E0, cmap='RdBu')
    plt.title('E_y / E0 (<-)')
    plt.xlabel('y')
    plt.ylabel('x')
    plt.colorbar()
    plt.show()

# maximum electric field magnitude in the domain
def Emax(Ex, Ey, eps_r):
    E_mag = npa.sqrt(npa.square(npa.abs(Ex)) + npa.square(npa.abs(Ey)))
    material_density = (eps_r - 1) / (eps_max - 1)
    return npa.max(E_mag * material_density)

# average electric field magnitude in the domain
def Eavg(Ex, Ey):
    E_mag = npa.sqrt(npa.square(npa.abs(Ex)) + npa.square(npa.abs(Ey)))
    return npa.mean(E_mag)

# defines the acceleration gradient as a function of the relative permittivity grid
def accel_gradient(eps_arr):

    # set the permittivity of the FDFD and solve the fields
    F.eps_r = eps_arr.reshape((Nx, Ny))
    Ex, Ey, Hz = F.solve(source)

    # compute the gradient and normalize if you want
    G = npa.sum(Ey * eta / Ny) / Emax(Ex, Ey, eps_r)
    return -np.abs(G)

# define the gradient for autograd
grad_g = jacobian(accel_gradient)

# optimization
NIter = 10
bounds_eps = [(1, eps_max) if design_region.flatten()[i] == 1 else (1,1) for i in range(eps_r.size)]
minimize(accel_gradient, eps_r.flatten(), args=(), method='L-BFGS-B', jac=grad_g,
    bounds=bounds_eps, tol=None, callback=None,
    options={'disp': True, 'maxcor': 10, 'ftol': 2.220446049250313e-09,
             'gtol': 1e-05, 'eps': 1e-08, 'maxfun': 15000, 'maxiter': NIter,
             'iprint': -1, 'maxls': 20})

# plot the final permittivity
N_per = 10
eps_big = F.eps_r._value.copy()
for i in range(N_per):
    eps_big = np.concatenate([eps_big, eps_big])
plt.imshow(imarr(eps_big), cmap='nipy_spectral')
plt.colorbar()
plt.show()

# plot the accelerating fields
Ex, Ey, Hz = F.solve(source)
plt.imshow(np.real(imarr(Ey)) / E0, cmap='RdBu')
plt.title('E_y / E0 (<-)')
plt.xlabel('y')
plt.ylabel('x')
plt.colorbar()
plt.show()