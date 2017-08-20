import numpy as np

from chainer import cuda
from chainer import function
from chainer import utils
from chainer.utils import type_check


class Gauss(function.Function):
    def __init__(self):
        self.eps = None

    def check_type_forward(self, in_type):
        type_check.expect(in_type.size() == 2)

        m_type, v_type = in_type
        type_check.expect(m_type.shape == v_type.shape)

    def forward_cpu(self, inputs):
        self.retain_inputs(())

        mean, ln_var = inputs
        if self.eps is None:
            self.eps = np.random.standard_normal(mean.shape) \
                                .astype(np.float32)
        self.noise = np.exp(ln_var * mean.dtype.type(0.5)) * self.eps
        return utils.force_array(mean + self.noise),

    def forward_gpu(self, inputs):
        self.retain_inputs(())

        cupy = cuda.cupy
        mean, ln_var = inputs
        if self.eps is None:
            self.eps = cupy.random.standard_normal(
                ln_var.shape, dtype=mean.dtype)

        self.noise = cuda.cupy.empty_like(mean)
        self.noise = cuda.elementwise(
            'T v, T e', 'T noise',
            'noise = exp(v / 2) * e',
            'gaussian_forward'
        )(ln_var, self.eps)
        return mean + self.noise,

    def backward(self, inputs, grad_output):
        g, = grad_output
        return g, utils.force_array(g * self.noise * g.dtype.type(0.5))


def gaussian(mean, ln_var):
    return Gauss()(mean, ln_var)
