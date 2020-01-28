
import tensorflow as tf

from conf import conf

tfk = tf.keras
K=tfk.backend

import numpy as np
from tensorflow.python.keras.engine.input_spec import InputSpec
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import tensor_shape
from tensorflow.python.ops import math_ops
from tensorflow.python.ops import gen_math_ops
from tensorflow.python.ops import nn


class MonotonicOnlyConstraint(tfk.constraints.Constraint):
    def __init(self):
        pass

    def __call__(self, w):
        return w*w


class MonotonicConstraint(tfk.constraints.Constraint):
    def __init__(self, mon_size_in, non_mon_size_in, mon_size_out, non_mon_size_out):
        self._mon_size_in = mon_size_in
        self._non_mon_size_in = non_mon_size_in
        self._mon_size_out = mon_size_out
        self._non_mon_size_out = non_mon_size_out

    def __call__(self, w):
        mask_1_mon = np.zeros((self._mon_size_in + self._non_mon_size_in, self._mon_size_out + self._non_mon_size_out),
                              dtype=getattr(np, "float%s" % conf.precision))
        mask_1_mon[:self._mon_size_in, :self._mon_size_out] = 1.0

        mask_1_non_mon = np.zeros((self._mon_size_in + self._non_mon_size_in, self._mon_size_out + self._non_mon_size_out),
                                  dtype=getattr(np, "float%s" % conf.precision))
        mask_1_non_mon[self._mon_size_in:, :] = 1.0

        w_mon = w * mask_1_mon * w
        w_non_mon = w * mask_1_non_mon
        w = w_mon + w_non_mon
        return w


class Dense(tfk.layers.Layer):
  """Just your regular densely-connected NN layer.

  `Dense` implements the operation:
  `output = activation(dot(input, kernel) + bias)`
  where `activation` is the element-wise activation function
  passed as the `activation` argument, `kernel` is a weights matrix
  created by the layer, and `bias` is a bias vector created by the layer
  (only applicable if `use_bias` is `True`).

  Note: If the input to the layer has a rank greater than 2, then
  it is flattened prior to the initial dot product with `kernel`.

  Example:

  ```python
  # as first layer in a sequential model:
  model = Sequential()
  model.add(Dense(32, input_shape=(16,)))
  # now the model will take as input arrays of shape (*, 16)
  # and output arrays of shape (*, 32)

  # after the first layer, you don't need to specify
  # the size of the input anymore:
  model.add(Dense(32))
  ```

  Arguments:
    units: Positive integer, dimensionality of the output space.
    activation: Activation function to use.
      If you don't specify anything, no activation is applied
      (ie. "linear" activation: `a(x) = x`).
    use_bias: Boolean, whether the layer uses a bias vector.
    kernel_initializer: Initializer for the `kernel` weights matrix.
    bias_initializer: Initializer for the bias vector.
    kernel_regularizer: Regularizer function applied to
      the `kernel` weights matrix.
    bias_regularizer: Regularizer function applied to the bias vector.
    activity_regularizer: Regularizer function applied to
      the output of the layer (its "activation")..
    kernel_constraint: Constraint function applied to
      the `kernel` weights matrix.
    bias_constraint: Constraint function applied to the bias vector.

  Input shape:
    N-D tensor with shape: `(batch_size, ..., input_dim)`.
    The most common situation would be
    a 2D input with shape `(batch_size, input_dim)`.

  Output shape:
    N-D tensor with shape: `(batch_size, ..., units)`.
    For instance, for a 2D input with shape `(batch_size, input_dim)`,
    the output would have shape `(batch_size, units)`.
  """

  def __init__(self,
               units,
               activation=None,
               use_bias=True,
               kernel_initializer='glorot_uniform',
               bias_initializer='zeros',
               kernel_regularizer=None,
               bias_regularizer=None,
               activity_regularizer=None,
               kernel_constraint=None,
               bias_constraint=None,
               **kwargs):
    if 'input_shape' not in kwargs and 'input_dim' in kwargs:
      kwargs['input_shape'] = (kwargs.pop('input_dim'),)

    super(Dense, self).__init__(
        activity_regularizer=tfk.regularizers.get(activity_regularizer), **kwargs)
    self.units = int(units)
    self.activation = tfk.activations.get(activation)
    self.use_bias = use_bias
    self.kernel_initializer = tfk.initializers.get(kernel_initializer)
    self.bias_initializer = tfk.initializers.get(bias_initializer)
    self.kernel_regularizer = tfk.regularizers.get(kernel_regularizer)
    self.bias_regularizer = tfk.regularizers.get(bias_regularizer)
    self.kernel_constraint = tfk.constraints.get(kernel_constraint)
    self.bias_constraint = tfk.constraints.get(bias_constraint)

    self.supports_masking = True
    self.input_spec = InputSpec(min_ndim=2)

  def build(self, input_shape):
    dtype = dtypes.as_dtype(self.dtype or K.floatx())
    if not (dtype.is_floating or dtype.is_complex):
      raise TypeError('Unable to build `Dense` layer with non-floating point '
                      'dtype %s' % (dtype,))
    input_shape = tensor_shape.TensorShape(input_shape)
    if tensor_shape.dimension_value(input_shape[-1]) is None:
      raise ValueError('The last dimension of the inputs to `Dense` '
                       'should be defined. Found `None`.')
    last_dim = tensor_shape.dimension_value(input_shape[-1])
    self.input_spec = InputSpec(min_ndim=2,
                                axes={-1: last_dim})
    self.kernel = self.add_weight(
        'kernel',
        shape=[last_dim, self.units],
        initializer=self.kernel_initializer,
        regularizer=self.kernel_regularizer,
        dtype=self.dtype,
        trainable=True)

    if self.use_bias:
      self.bias = self.add_weight(
          'bias',
          shape=[self.units,],
          initializer=self.bias_initializer,
          regularizer=self.bias_regularizer,
          dtype=self.dtype,
          trainable=True)
    else:
      self.bias = None
    self.built = True

  def call(self, inputs):
    rank = len(inputs.shape)
    kernel = self.kernel
    if self.kernel_constraint is not None:
        kernel = self.kernel_constraint(kernel)
    if rank > 2:
      # Broadcasting is required for the inputs.
      outputs = tfk.standard_ops.tensordot(inputs, kernel, [[rank - 1], [0]])
      # Reshape the output back to the original ndim of the input.
      if not tfk.context.executing_eagerly():
        shape = inputs.shape.as_list()
        output_shape = shape[:-1] + [self.units]
        outputs.set_shape(output_shape)
    else:
      inputs = math_ops.cast(inputs, self._compute_dtype)
      if K.is_sparse(inputs):
        outputs = tfk.sparse_ops.sparse_tensor_dense_matmul(inputs, kernel)
      else:
        outputs = gen_math_ops.mat_mul(inputs, kernel)
    if self.use_bias:
      outputs = nn.bias_add(outputs, self.bias)
    if self.activation is not None:
      return self.activation(outputs)  # pylint: disable=not-callable
    return outputs

  def compute_output_shape(self, input_shape):
    input_shape = tensor_shape.TensorShape(input_shape)
    input_shape = input_shape.with_rank_at_least(2)
    if tensor_shape.dimension_value(input_shape[-1]) is None:
      raise ValueError(
          'The innermost dimension of input_shape must be defined, but saw: %s'
          % input_shape)
    return input_shape[:-1].concatenate(self.units)

  def get_config(self):
    config = {
        'units': self.units,
        'activation': tfk.activations.serialize(self.activation),
        'use_bias': self.use_bias,
        'kernel_initializer': tfk.initializers.serialize(self.kernel_initializer),
        'bias_initializer': tfk.initializers.serialize(self.bias_initializer),
        'kernel_regularizer': tfk.regularizers.serialize(self.kernel_regularizer),
        'bias_regularizer': tfk.regularizers.serialize(self.bias_regularizer),
        'activity_regularizer':
            tfk.regularizers.serialize(self.activity_regularizer),
        'kernel_constraint': tfk.constraints.serialize(self.kernel_constraint),
        'bias_constraint': tfk.constraints.serialize(self.bias_constraint)
    }
    base_config = super(Dense, self).get_config()
    return dict(list(base_config.items()) + list(config.items()))


class MyDense(tfk.layers.Layer):
  """Just your regular densely-connected NN layer.

  `Dense` implements the operation:
  `output = activation(dot(input, kernel) + bias)`
  where `activation` is the element-wise activation function
  passed as the `activation` argument, `kernel` is a weights matrix
  created by the layer, and `bias` is a bias vector created by the layer
  (only applicable if `use_bias` is `True`).

  Note: If the input to the layer has a rank greater than 2, then
  it is flattened prior to the initial dot product with `kernel`.

  Example:

  ```python
  # as first layer in a sequential model:
  model = Sequential()
  model.add(Dense(32, input_shape=(16,)))
  # now the model will take as input arrays of shape (*, 16)
  # and output arrays of shape (*, 32)

  # after the first layer, you don't need to specify
  # the size of the input anymore:
  model.add(Dense(32))
  ```

  Arguments:
    units: Positive integer, dimensionality of the output space.
    activation: Activation function to use.
      If you don't specify anything, no activation is applied
      (ie. "linear" activation: `a(x) = x`).
    use_bias: Boolean, whether the layer uses a bias vector.
    kernel_initializer: Initializer for the `kernel` weights matrix.
    bias_initializer: Initializer for the bias vector.
    kernel_regularizer: Regularizer function applied to
      the `kernel` weights matrix.
    bias_regularizer: Regularizer function applied to the bias vector.
    activity_regularizer: Regularizer function applied to
      the output of the layer (its "activation")..
    kernel_constraint: Constraint function applied to
      the `kernel` weights matrix.
    bias_constraint: Constraint function applied to the bias vector.

  Input shape:
    N-D tensor with shape: `(batch_size, ..., input_dim)`.
    The most common situation would be
    a 2D input with shape `(batch_size, input_dim)`.

  Output shape:
    N-D tensor with shape: `(batch_size, ..., units)`.
    For instance, for a 2D input with shape `(batch_size, input_dim)`,
    the output would have shape `(batch_size, units)`.
  """

  def __init__(self,
               units,
               activation=None,
               use_bias=True,
               kernel_initializer='glorot_uniform',
               bias_initializer='zeros',
               kernel_regularizer=None,
               bias_regularizer=None,
               activity_regularizer=None,
               kernel_constraint=None,
               bias_constraint=None,
               **kwargs):
    if 'input_shape' not in kwargs and 'input_dim' in kwargs:
      kwargs['input_shape'] = (kwargs.pop('input_dim'),)

    super(MyDense, self).__init__(
        activity_regularizer=tfk.regularizers.get(activity_regularizer), **kwargs)
    self.units = int(units)
    self.activation = tfk.activations.get(activation)
    self.use_bias = use_bias
    self.kernel_initializer = tfk.initializers.get(kernel_initializer)
    self.bias_initializer = tfk.initializers.get(bias_initializer)
    self.kernel_regularizer = tfk.regularizers.get(kernel_regularizer)
    self.bias_regularizer = tfk.regularizers.get(bias_regularizer)
    self.kernel_constraint = tfk.constraints.get(kernel_constraint)
    self.bias_constraint = tfk.constraints.get(bias_constraint)

    self.supports_masking = True
    self.input_spec = InputSpec(min_ndim=2)

  def build(self, input_shape):
    dtype = dtypes.as_dtype(self.dtype or K.floatx())
    if not (dtype.is_floating or dtype.is_complex):
      raise TypeError('Unable to build `Dense` layer with non-floating point '
                      'dtype %s' % (dtype,))
    input_shape = tensor_shape.TensorShape(input_shape)
    if tensor_shape.dimension_value(input_shape[-1]) is None:
      raise ValueError('The last dimension of the inputs to `Dense` '
                       'should be defined. Found `None`.')
    last_dim = tensor_shape.dimension_value(input_shape[-1])
    self.input_spec = InputSpec(min_ndim=2,
                                axes={-1: last_dim})
    self.kernel = self.add_weight(
        'kernel',
        shape=[last_dim, self.units],
        initializer=self.kernel_initializer,
        regularizer=self.kernel_regularizer,
        dtype=self.dtype,
        trainable=True)

    if self.use_bias:
      self.bias = self.add_weight(
          'bias',
          shape=[self.units,],
          initializer=self.bias_initializer,
          regularizer=self.bias_regularizer,
          dtype=self.dtype,
          trainable=True)
    else:
      self.bias = None
    self.built = True

  def call(self, inputs):
    kernel = self.kernel
    if self.kernel_constraint is not None:
      kernel = self.kernel_constraint(self.kernel)
    outputs = K.dot(inputs, kernel)

    if self.use_bias:
      outputs = nn.bias_add(outputs, self.bias)
    if self.activation is not None:
      outputs = self.activation(outputs)
    return outputs

  def compute_output_shape(self, input_shape):
    input_shape = tensor_shape.TensorShape(input_shape)
    input_shape = input_shape.with_rank_at_least(2)
    if tensor_shape.dimension_value(input_shape[-1]) is None:
      raise ValueError(
          'The innermost dimension of input_shape must be defined, but saw: %s'
          % input_shape)
    return input_shape[:-1].concatenate(self.units)

  def get_config(self):
    config = {
        'units': self.units,
        'activation': tfk.activations.serialize(self.activation),
        'use_bias': self.use_bias,
        'kernel_initializer': tfk.initializers.serialize(self.kernel_initializer),
        'bias_initializer': tfk.initializers.serialize(self.bias_initializer),
        'kernel_regularizer': tfk.regularizers.serialize(self.kernel_regularizer),
        'bias_regularizer': tfk.regularizers.serialize(self.bias_regularizer),
        'activity_regularizer':
            tfk.regularizers.serialize(self.activity_regularizer),
        'kernel_constraint': tfk.constraints.serialize(self.kernel_constraint),
        'bias_constraint': tfk.constraints.serialize(self.bias_constraint)
    }
    base_config = super(MyDense, self).get_config()
    return dict(list(base_config.items()) + list(config.items()))