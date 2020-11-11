"""A popular speaker recognition and diarization model.

Authors
 * Nauman Dawalatabad 2020
 * Mirco Ravanelli 2020
"""

# import os
import torch  # noqa: F401
import speechbrain as sb


class Xvector(sb.nnet.containers.Sequential):
    """This model extracts XVectors for speaker recognition and diarization.

    Arguments
    ---------
    input_shape : tuple
        Expected shape of an example input.
    activation : torch class
        A class for constructing the activation layers.
    tdnn_blocks : int
        Number of time delay neural (TDNN) layers.
    tdnn_channels : list of ints
        Output channels for TDNN layer.
    tdnn_kernel_sizes : list of ints
        List of kernel sizes for each TDNN layer.
    tdnn_dilations : list of ints
        List of dialations for kernels in each TDNN layer.
    lin_neurons : int
        Number of neurons in linear layers.

    Example
    -------
    >>> input_feats = torch.rand([5, 10, 24])
    >>> compute_xvect = Xvector(input_shape=input_feats.shape)
    >>> outputs = compute_xvect(input_feats)
    >>> outputs.shape
    torch.Size([5, 1, 512])
    """

    def __init__(
        self,
        input_shape,
        activation=torch.nn.LeakyReLU,
        tdnn_blocks=5,
        tdnn_channels=[512, 512, 512, 512, 1500],
        tdnn_kernel_sizes=[5, 3, 3, 1, 1],
        tdnn_dilations=[1, 2, 3, 1, 1],
        lin_neurons=512,
    ):
        super().__init__(input_shape=input_shape)

        if tdnn_blocks > 0:
            self.append(sb.nnet.containers.Sequential, layer_name="TDNN")

        # TDNN layers
        for block_index in range(tdnn_blocks):
            block_name = f"block_{block_index}"
            self.TDNN.append(
                sb.nnet.containers.Sequential, layer_name=block_name
            )
            self.TDNN[block_name].append(
                sb.nnet.CNN.Conv1d,
                out_channels=tdnn_channels[block_index],
                kernel_size=tdnn_kernel_sizes[block_index],
                dilation=tdnn_dilations[block_index],
                layer_name="conv",
            )
            self.TDNN[block_name].append(activation(), layer_name="act")
            self.TDNN[block_name].append(
                sb.nnet.normalization.BatchNorm1d, layer_name="norm"
            )

        # Statistical pooling
        self.append(sb.nnet.pooling.StatisticsPooling(), layer_name="stat_pool")

        # Final linear transformation
        self.append(
            sb.nnet.linear.Linear, n_neurons=lin_neurons, layer_name="out"
        )


class Classifier(sb.nnet.containers.Sequential):
    """This class implements the last MLP on the top of xvector features.

    Arguments
    ---------
    input_shape : tuple
        Expected shape of an example input.
    activation : torch class
        A class for constructing the activation layers.
    lin_blocks : int
        Number of linear layers.
    lin_neurons : int
        Number of neurons in linear layers.
    out_neurons : int
        Number of ouput neurons.

    Example
    -------
    >>> input_feats = torch.rand([5, 10, 24])
    >>> compute_xvect = Xvector(input_shape=input_feats.shape)
    >>> xvects = compute_xvect(input_feats)
    >>> classify = Classifier(input_shape=xvects.shape)
    >>> output = classify(xvects)
    >>> output.shape
    torch.Size([5, 1, 1211])
    """

    def __init__(
        self,
        input_shape,
        activation=torch.nn.LeakyReLU,
        lin_blocks=1,
        lin_neurons=512,
        out_neurons=1211,
    ):
        super().__init__(input_shape=input_shape)

        self.append(activation(), layer_name="act")
        self.append(sb.nnet.normalization.BatchNorm1d, layer_name="norm")

        if lin_blocks > 0:
            self.append(sb.nnet.containers.Sequential, layer_name="DNN")

        for block_index in range(lin_blocks):
            block_name = f"block_{block_index}"
            self.DNN.append(
                sb.nnet.containers.Sequential, layer_name=block_name
            )
            self.DNN[block_name].append(
                sb.nnet.linear.Linear,
                n_neurons=lin_neurons,
                bias=True,
                layer_name="linear",
            )
            self.DNN[block_name].append(activation(), layer_name="act")
            self.DNN[block_name].append(
                sb.nnet.normalization.BatchNorm1d, layer_name="norm"
            )

        # Final Softmax classifier
        self.append(
            sb.nnet.linear.Linear, n_neurons=out_neurons, layer_name="out"
        )
        self.append(
            sb.nnet.activations.Softmax(apply_log=True), layer_name="softmax"
        )


class Discriminator(sb.nnet.containers.Sequential):
    """This class implements a discriminator on the top of xvector features.

    Arguments
    ---------
    device : str
        Device used e.g. "cpu" or "cuda"
    activation : torch class
        A class for constructing the activation layers.
    lin_blocks : int
        Number of linear layers.
    lin_neurons : int
        Number of neurons in linear layers.

    Example
    -------
    >>> input_feats = torch.rand([5, 10, 24])
    >>> compute_xvect = Xvector(input_feats.shape)
    >>> xvects = compute_xvect(input_feats)
    >>> classify = Classifier(xvects.shape)
    >>> output = classify(xvects)
    >>> output.shape
    torch.Size([5, 1, 1211])
    """

    def __init__(
        self,
        input_shape,
        activation=torch.nn.LeakyReLU,
        lin_blocks=1,
        lin_neurons=512,
        out_neurons=1,
    ):
        super().__init__(input_shape=input_shape)

        if lin_blocks > 0:
            self.append(sb.nnet.containers.Sequential, layer_name="DNN")

        for block_index in range(lin_blocks):
            block_name = f"block_{block_index}"
            self.DNN.append(
                sb.nnet.containers.Sequential, layer_name=block_name
            )
            self.DNN[block_name].append(
                sb.nnet.linear.Linear,
                n_neurons=lin_neurons,
                bias=True,
                combine_dims=False,
                layer_name="linear",
            )
            self.DNN[block_name].append(
                sb.nnet.normalization.BatchNorm1d, layer_name="norm"
            )
            self.DNN[block_name].append(activation(), layer_name="act")

        # Final Layer (sigmoid not included)
        self.append(
            sb.nnet.linear.Linear, n_neurons=out_neurons, layer_name="out"
        )
