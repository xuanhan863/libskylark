import numpy, numpy.random, scipy.linalg, scipy.stats
import utils
from math import sqrt, cos, pi
import skylark.io, skylark.metrics, skylark.sketch
import sys

class rls(object):
  """
  Class for solving Non-linear Regularized Least Squares problems using
  the provided kernel.
  
  Example
  -------
  
  Read a digit classification dataset
  
  >>> X, Y = skylark.io.libsvm(sys.argv[1]).read()
  
  Set Regularization Parameter and Gaussian Kernel Bandwidth
  
  >>> regularization = 0.001
  >>> bandwidth = 10.0
  
  Setup kernel:
  
  >>> import kernels
  >>> kernel = kernels.gaussian(X.shape[1], bandwidth)

  Build a model on 1000 training examples
  
  >>> model = skylark.ml.nonlinear.rls(kernel)
  >>> model.train(X[1:1000,:], Y[1:1000], regularization)	
	
  Make Predictions on 1000 test examples
  
  >>> predictions = model.predict(X[1001:2000,:])
  
  Compute classification accuracy
  
  >>> accuracy = skylark.metrics.classification_accuracy(predictions, Y[1001:2000])
  >>> print "RLS Accuracy=%f%%" % accuracy
  RLS Accuracy=92.792793%
  """
  def __init__(self, kernel):
    self._model = {}
    self._kernel = kernel
    
  def train(self, X, Y, regularization=1,  multiclass=True):
    """
    Train the model.
    
    
    Parameters
    ----------
    X: m x n input matrix
    
    Y: m x 1 label vector (if multi-class classification problem, 
       labels are from 0 to K-1 - trains one-vs-rest)
    
    regularization: regularization parameter

    multiclass: is it a multiclass problem or not
   
    
    Returns
    --------
    Nothing. Internally sets the model parameters.
    
    """
    m,n = X.shape
    K = self._kernel.gram(X)
    I = numpy.identity(m)
    if multiclass:
      Y = utils.dummycoding(Y)
      Y = 2*Y - 1
    A = K + regularization*I
    alpha = scipy.linalg.solve(A, Y, sym_pos=True)
    self.model = {"kernel": self._kernel, 
                  "alpha": alpha, 
                  "regularization": regularization, 
                  "data": X, 
                  "multiclass":multiclass}
      
  def predict(self, Xt):
    """
    Make Predictions on test data
    
    predict(Xt)
    
    Parameters
    ----------
    Xt: m x n input test matrix
    
    Returns
    -------
    m x 1 array of predictions on the test set.
    """
    kernel = self._kernel
    K = kernel.gram(self.model["data"], Xt)
    pred = K*self.model["alpha"]
    if self.model["multiclass"]:
      pred = numpy.argmax(numpy.array(pred), axis=1)+1
    return pred
    
class sketchrls(object):
  """
  Class for sketching based (aka random features) Non-linear Regularized Least 
  Squares problems,
  
  Example
  -------

  Read a digit classification dataset
  
  >>> X, Y = skylark.io.libsvm(sys.argv[1]).read()
  
  Set Regularization Parameter and Gaussian Kernel Bandwidth
  
  >>> regularization = 0.001
  >>> bandwidth = 10.0
  
  Setup kernel:
  
  >>> import kernels
  >>> kernel = kernels.gaussian(X.shape[1], bandwidth)
  
  Set number of random features
  
  >>> random_features = 100
	
  Build a model on 1000 training examples
  
  >>> model = skylark.ml.nonlinear.sketchrls(kernel)
  >>> model.train(X[1:1000,:], Y[1:1000], random_features, regularization)	
  
  Make Predictions on 1000 test examples
  
  >>> predictions = model.predict(X[1001:2000,:])
  
  Compute classification accuracy
  
  >>> accuracy = skylark.metrics.classification_accuracy(predictions, Y[1001:2000])
  >>> print "SketchedRLS Accuracy=%f%%" % accuracy
  SketchedRLS Accuracy=86.386386%
  """
  
  def __init__(self, kernel):
    self.model = {}
    self._kernel = kernel				

  def train(self, X, Y, random_features=100, regularization=1, multiclass=True):
    """
    Train the model.
    
    
    Parameters
    ----------
    X: m x n input matrix
    
    Y: m x 1 label vector (if multi-class classification problem, 
       labels are from 0 to K-1 - trains one-vs-rest)
    
    regularization: regularization parameter

    multiclass: is it a multiclass problem or not

    random_features: number of random features to use.
    
    Returns
    --------
    Nothing. Internally sets the model parameters.
    
    """

    self._rft = self._kernel.rft(random_features)
    Z = self._rft / X
    
    I = numpy.identity(random_features)
    if multiclass:
      Y= utils.dummycoding(Y)
      Y = 2*Y - 1
      
    A = numpy.dot(Z.T, Z) + regularization*I
    weights = scipy.linalg.solve(A, numpy.dot(Z.T, Y), sym_pos=True)
    self.model = {"kernel": self._kernel,
                  "rft": self._rft,
                  "weights": weights, 
                  "random_features": random_features,  
                  "regularization": regularization, 
                  "multiclass":multiclass}
      
  def predict(self, Xt):
    """
    Make predictions on test data
    
    Parameters
    ----------
    Xt: m x n input test matrix
    
    Returns
    -------
    m x 1 array of predictions on the test set.
    """
    Zt = self._rft / Xt
    pred = numpy.dot(Zt, self.model["weights"])
    if self.model["multiclass"]:
      pred = numpy.argmax(numpy.array(pred), axis=1)+1
    return pred
    
class nystromrls(object):
      
  def __init__(self, kernel):
    self.model = {}
    self._kernel = kernel
    
  def train(self,X, Y, random_features=100, regularization=1, bandwidth=1, 
            probdist='uniform', multiclass=True):
    """
    :param probdist: probability distribution of rows. Either 'uniform' or 'leverages'.
    :param l: number of Nystrom random samples to take
    :param k: rank-k approximation to the Gram matrix of the sampled data is used
    """
    m,n = X.shape
    nz_values = range(0, m)
    
    #uniform
    if probdist == 'uniform':
      nz_prob_dist = numpy.ones((m,1))/m
    elif probdist ==  'leverages':
      # TODO the following is probably not correct as leverages are define w.r. 
      #      to rank.
      K = self._kernel.gram(X)
      Im = numpy.identity(m)
      nz_prob_dist = numpy.diag(K*scipy.linalg.inv(K+regularization*Im))
      nz_prob_dist = nz_prob_dist/sum(nz_prob_dist)
    else:
      raise skylark.errors.InvalidParamterError("Unknown probability distribution strategy")

    SX = skylark.sketch.NonUniformSampler(m, random_features, nz_prob_dist) * X
    K_II = self._kernel.gram(SX)
    I = numpy.identity(random_features)
    eps = 1e-8
    (evals, evecs) = scipy.linalg.eigh(K_II + eps*I)
    Z = self._kernel.gram(SX, X)
    U = (evecs*numpy.diagflat(1.0/numpy.sqrt(evals)))
    Z = Z*U
    if multiclass:
      Y= utils.dummycoding(Y)
      Y = 2*Y - 1
      
    A = numpy.dot(Z.T, Z) + regularization*I
    weights = scipy.linalg.solve(A, numpy.dot(Z.T, Y), sym_pos=True)
    self.model = {"kernel": self._kernel, 
                  "weights": weights, 
                  "random_features": random_features,  
                  "regularization": regularization, 
                  "multiclass":multiclass, 
                  "SX":SX, 
                  "U":U }
    
  def predict(self, Xt):
    """
    Make predictions on test data
    
    Parameters
    ----------
    Xt: m x n input test matrix
    
    Returns
    -------
    m x 1 array of predictions on the test set.
    """
    Zt = self._kernel.gram(self.model["SX"], Xt)*self.model["U"]
    pred = Zt * self.model["weights"]
    if self.model["multiclass"]:
      pred = numpy.argmax(numpy.array(pred), axis=1)+1
    return pred
    
# Small test problem    
if __name__=="__main__":
  import kernels

  X, Y = skylark.io.libsvm(sys.argv[1]).read()
  regularization= float(sys.argv[2])
  bandwidth = float(sys.argv[3])
  randomfeatures = int(sys.argv[4])
  trn = int(sys.argv[5])

  # For now we support only dense matrices in pure python
  X = X.todense()
  
  kernel = kernels.Gaussian(X.shape[1], bandwidth)
  model = rls(kernel)
  model.train(X[1:trn,:], Y[1:trn], regularization)	
  predictions = model.predict(X[trn+1:,:])
  accuracy = skylark.metrics.classification_accuracy(predictions, Y[trn+1:])
  print "RLS Accuracy=%f%%" % accuracy

  model = sketchrls(kernel)
  model.train(X[1:trn,:], Y[1:trn], randomfeatures, regularization)	
  predictions = model.predict(X[trn+1:,:])
  accuracy = skylark.metrics.classification_accuracy(predictions, Y[trn+1:])
  print "SketchedRLS Accuracy=%f%%" % accuracy
  
  model = nystromrls(kernel)
  model.train(X[1:trn,:], Y[1:trn], randomfeatures, regularization, probdist = 'uniform')
  predictions = model.predict(X[trn+1:,:])
  accuracy = skylark.metrics.classification_accuracy(predictions, Y[trn+1:])
  print "Nystrom uniform Accuracy=%f%%" % accuracy
  	
  model = nystromrls(kernel)
  model.train(X[1:trn,:], Y[1:trn], randomfeatures, regularization, probdist = 'leverages')
  predictions = model.predict(X[trn+1:,:])
  accuracy = skylark.metrics.classification_accuracy(predictions, Y[trn+1:])
  print "Nystrom leverages Accuracy=%f%%" % accuracy
