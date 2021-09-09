import numpy as np
import os
import tensorflow as tf
import solvers  as solv
import networks as net
import models as mod
import multiprocessing
import sys
import time

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

_MULTIPROCESSING_CORE_COUNT = multiprocessing.cpu_count()
print("args", sys.argv)

d = 1 
xInit= np.ones(d,dtype=np.float32) 
nbLayer= 2  
print("nbLayer " ,nbLayer)
rescal=1.
T=1.

batchSize= 2
batchSizeVal= 2
num_epoch=2
num_epochExtNoLast =2
num_epochExtLast= 2
initialLearningRateLast = 1e-2
initialLearningRateNoLast = 1e-3
nbOuterLearning =10
nTest = 1
ckpt_bsde = 'save_bounded_fnlm2dbdp/BoundedFNLM2DBDPd1nbNeur11nbHL2ndt22Alpha100BSDE_1'
ckpt_gam = 'save_bounded_fnlm2dbdp/BoundedFNLM2DBDPd1nbNeur11nbHL2ndt22Alpha100Gam_1'
#ckpt_bsde = 'save_bounded_fnlm2dbdp/BoundedFNLM2DBDPd1nbNeur11nbHL2ndt22Alpha100BSDE_1'
#ckpt_gam = 'save_bounded_fnlm2dbdp/BoundedFNLM2DBDPd1nbNeur11nbHL2ndt22Alpha100Gam_1'
weights_step = 1
n_layers_freeze = 2

lamb = np.array([1.5], dtype=np.float32)
eta = 0.5
theta = np.array([0.4], dtype=np.float32) 
gamma = np.array([0.2], dtype=np.float32) 
kappa = np.array([1.], dtype=np.float32)
sigma = np.array([1.], dtype=np.float32) 
nbNeuron = d + 10
sigScal =   np.array([1.], dtype=np.float32)

muScal = np.array([np.sum(theta*lamb)])
layerSize= nbNeuron*np.ones((nbLayer,), dtype=np.int32) 
# create the model
model = mod.ModelMerton(xInit, muScal, sigScal, T, theta, lamb, eta)

print(" WILL USE " + str(_MULTIPROCESSING_CORE_COUNT) + " THREADS ")
print("REAL IS ", model.Sol(0.,xInit), " DERIV", model.derSol(0.,xInit))

theNetwork = net.FeedForwardUZ(d,layerSize,tf.nn.tanh,
                                 num_layers_to_load_and_freeze=n_layers_freeze,
                                 path_saved_checkpoint=ckpt_bsde, weights_step=weights_step)
theNetworkGam = net.FeedForwardGam(d,layerSize,tf.nn.tanh,
                                 num_layers_to_load_and_freeze=n_layers_freeze,
                                 path_saved_checkpoint=ckpt_gam, weights_step=weights_step)

ndt = [ (2,2) ]


print("PDE Merton M2DBDP  Dim ", d,
      " layerSize " , layerSize,
      " rescal " ,rescal,
      "T ", T ,
      "batchsize ",batchSize,
      " batchSizeVal ", batchSizeVal,
      "num_epoch " , num_epoch,
      " num_epochExtNoLast ", num_epochExtNoLast  ,
      "num_epochExtLast " , num_epochExtLast,
      "VOL " , sigScal,
      "initialLearningRateLast" , initialLearningRateLast ,
      "initialLearningRateNoLast " , initialLearningRateNoLast)

# nest on ndt
for indt  in ndt:

    print("NBSTEP",indt)
    # create graph
    resol =  solv.PDEFNLSolve2OptGPU(model,
                                     T,
                                     indt[0],
                                     indt[1],
                                     theNetwork ,
                                     theNetworkGam,
                                     initialLearningRateLast=initialLearningRateLast,
                                     initialLearningRateNoLast = initialLearningRateNoLast)

    baseFile = "MertonM2DBDPd"+str(d)+"nbNeur"+str(layerSize[0])+"nbHL"+str(len(layerSize))+"ndt"+str(indt[0])+str(indt[1])+"eta"+str(int(eta*100))

    # Declare output folders for plots
    plotFol = os.path.join(os.getcwd(), "pictures")
    try:
        # Hierarchy folder does not exist, create
        os.mkdir(plotFol)

    except FileExistsError as e:
        pass

    plotFile = os.path.join(plotFol, baseFile)

    # Checkpoint save locations
    saveFolder = os.path.join(os.getcwd(), "save")

    Y0List = []
    for i in range(nTest):
        # train
        t0 = time.time()
        Y0, Z0, Gamma0  = resol.BuildAndtrainML( batchSize,
                                                 batchSizeVal,
                                                 num_epochExtNoLast=num_epochExtNoLast,
                                                 num_epochExtLast= num_epochExtLast ,
                                                 num_epoch=num_epoch,
                                                 nbOuterLearning=nbOuterLearning,
                                                 thePlot= plotFile ,
                                                 baseFile = baseFile,
                                                 saveDir= saveFolder)
        t1 = time.time()
        print(" NBSTEP", indt, " EstimMC Val is " , Y0,  " REAL IS ", model.Sol(0.,xInit),    " Z0 ", Z0," DERREAL IS  ",model.derSol(0.,xInit), "Gamma0 " , Gamma0,t1-t0)

        Y0List.append(Y0)
        print(Y0List)

    print("Y0", Y0List)
    yList = np.array(Y0List)
    yMean = np.mean(yList)
    print(" DNT ", indt , "MeanVal ", yMean, " Etyp ", np.sqrt(np.mean(np.power(yList-yMean,2.))))
