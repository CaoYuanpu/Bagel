import torch
import torch.distributions as dist
import torch.nn as nn
from torch.autograd import Variable

from .variational_autoencoder import VAE


class ConditionalVariationalAutoencoder(VAE):
    """
    P(x|y)
    """

    def __init__(self, variational: nn.Module, generative: nn.Module, n_sample=1):
        """
        :param variational: nn.Module; \mu, \sigma=variational(x), where z~N(\mu, \sigma^2)
        :param generative: nn.Module; \mu, \sigma=generative(z), where x~N(\mu, \sigma^2)
        """
        super().__init__(variational, generative, n_sample)

    def forward(self, *, n_sample=1, **kwargs):
        """
        In training phase, z = \sigma * z_std + z_mean, and sample \sigma from N(0, 1)
        In testing phase, sample z from Q(z|x)
        :param n_sample: positive integer
        :param kwargs:
            observe_x: in shape (batch_size, x_dims)
            observe_y: in shape (batch_size, y_dims)
        :return: P(x|z), Q(z|x), z_samples
        """
        x = kwargs.pop("observe_x")
        y = kwargs.pop("observe_y")
        if n_sample is None:
            n_sample = self.n_sample

        # observe_x_mean = torch.mean(x, -1, keepdim=True)
        # observer_x_std = torch.std(x, -1, keepdim=True)
        # cat = torch.cat([observe_x_mean, observer_x_std, (x - observe_x_mean) / observer_x_std, y], dim=-1)
        cat = torch.cat([x, y], dim=-1)

        z_mean, z_std = self.variational(cat)

        z_given_x_dist = dist.Normal(z_mean, z_std)
        if self.training: # this attribute is set by model.train() and model.eval()
            # reparameterize
            zero = Variable(torch.zeros(z_mean.size())).type_as(z_mean)
            one = Variable(torch.ones(z_std.size())).type_as(z_std)
            z = dist.Normal(zero, one).sample((n_sample, )) * z_std.unsqueeze(0) + z_mean.unsqueeze(0)
            assert z.size() == torch.Size((n_sample, *z_mean.size()))
        else:
            z = z_given_x_dist.sample((n_sample, ))

        y = y.expand(n_sample, -1, -1)
        # observer_x_std = observer_x_std.expand(n_sample, -1, -1)
        # observe_x_mean = observe_x_mean.expand(n_sample, -1, -1)
        cat = torch.cat([z, y], dim=-1)
        x_mean, x_std = self.generative(cat)
        x_given_z_dist = dist.Normal(x_mean, x_std)

        return x_given_z_dist, z_given_x_dist, z

    def penalty(self) -> Variable:
        return self.variational.penalty() + self.generative.penalty()


CVAE = ConditionalVariationalAutoencoder
