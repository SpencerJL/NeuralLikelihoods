from inspect import signature

import models.tensorflow.quadrature as quad
import tensorflow as tf

@tf.function
def mi(prob_fun, var1, var2, integrate_out=None, **kwargs):
    return quad.mi(prob_fun, var1, var2, integrate_out, **kwargs)

@tf.function
def mi_all_vars(prob_fun, **kwargs):
    all_vars = [param_name for param_name in signature(prob_fun).parameters.keys()]
    vars_size = len(all_vars)
    mi_list = []
    indices = []
    with tf.device("/cpu:0"):
        for var_i in range(vars_size):
            for var_j in range(var_i + 1, vars_size):
                var_i_name = all_vars[var_i]
                var_j_name = all_vars[var_j]
                indices.append([var_i,var_j])
                integrate_out = list(set(all_vars) - set([var_i_name, var_j_name]))
                mi_list.append(mi(prob_fun, var1=var_i_name, var2=var_j_name, integrate_out=integrate_out,
                                            **kwargs))

    return tf.scatter_nd(indices, mi_list, [vars_size,vars_size])

def constrain_cdf(cdf, name="cdf"):
    # constraining using these constants so quantiles can be computed
    return tf.clip_by_value(cdf,  1e-37, 1.0 - 1e-7, name=name)
