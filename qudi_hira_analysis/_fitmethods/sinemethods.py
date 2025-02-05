# -*- coding: utf-8 -*-
"""
This file contains methods for sine fitting, these methods
are imported by class FitLogic.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
from lmfit.models import Model
from scipy import signal


def get_ft_windows():
    """ Retrieve the available windows to be applied on signal data before FT.

    @return: dict with keys being the window name and items being again a dict
             containing the actual function and the normalization factor to
             calculate correctly the amplitude spectrum in the Fourier Transform

    To find out the amplitude normalization factor check either the scipy
    implementation on
        https://github.com/scipy/scipy/blob/v0.15.1/scipy/signal/windows.py#L336
    or just perform a sum of the window (oscillating parts of the window should
    be averaged out and constant offset factor will remain):
        MM=1000000  # choose a big number
        print(sum(signal.hanning(MM))/MM)
    """

    win = {'none': {'func': np.ones, 'ampl_norm': 1.0},
           'hamming': {'func': signal.hamming, 'ampl_norm': 1.0/0.54},
           'hann': {'func': signal.hann, 'ampl_norm': 1.0/0.5},
           'blackman': {'func': signal.blackman, 'ampl_norm': 1.0/0.42},
           'triang': {'func': signal.triang, 'ampl_norm': 1.0/0.5},
           'flattop': {'func': signal.flattop, 'ampl_norm': 1.0/0.2156},
           'bartlett': {'func': signal.bartlett, 'ampl_norm': 1.0/0.5},
           'parzen': {'func': signal.parzen, 'ampl_norm': 1.0/0.375},
           'bohman': {'func': signal.bohman, 'ampl_norm': 1.0/0.4052847},
           'blackmanharris': {'func': signal.blackmanharris, 'ampl_norm': 1.0/0.35875},
           'nuttall': {'func': signal.nuttall, 'ampl_norm': 1.0/0.3635819},
           'barthann': {'func': signal.barthann, 'ampl_norm': 1.0/0.5}}
    return win


def compute_ft(x_val, y_val, zeropad_num=0, window='none', base_corr=True, psd=False):
    """ Compute the Discrete fourier Transform of the power spectral density

    @param numpy.array x_val: 1D array
    @param numpy.array y_val: 1D array of same size as x_val
    @param int zeropad_num: optional, zeropadding (adding zeros to the end of
                            the array). zeropad_num >= 0, the size of the array
                            which is add to the end of the y_val before
                            performing the Fourier Transform (FT). The
                            resulting array will have the length
                                (len(y_val)/2)*(zeropad_num+1)
                            Note that zeropadding will not change or add more
                            information to the dft, it will solely interpolate
                            between the dft_y values (corresponds to a Sinc
                            interpolation method).
                            Set zeropad_num=1 to obtain output arrays which
                            have the same size as the input arrays.
                            Default is zeropad_num=0.
    @param str window: optional, the window function which should be applied to
                       the y values before Fourier Transform is calculated.
    @param bool base_corr: Select whether baseline correction shoud be performed
                           before calculating the FT.
    @param bool psd: optional, select whether the Discrete Fourier Transform or
                     the Power Spectral Density (PSD, which is just the FT of
                     the absolute square of the y-values) should be computed.
                     Default is psd=False.

    @return: tuple(dft_x, dft_y):
                be aware that the return arrays' length depend on the zeropad
                number like
                    len(dft_x) = len(dft_y) = (len(y_val)/2)*(zeropad_num+1)

    Pay attention that the return values of the FT have only half of the
    entries compared to the used signal input (if zeropad=0).

    In general, a window function should be applied on the y data before
    calculating the FT, to reduce spectral leakage. The Hann window for
    instance is almost never a bad choice. Use it like window='hann'

    Keep always in mind the relation to the Fourier transform space:
        T = delta_t * N_samples
    where delta_t is the distance between the time points and N_samples are the
    amount of points in the time domain. Consequently the sample rate is
        f_samplerate = T / N_samples

    Keep also in mind that the FT returns value from 0 to f_samplerate, or
        equivalently -f_samplerate/2 to f_samplerate/2.

    Difference between PSD and DFT:
    The power spectral density (PSD) describes how the power of your signal is
    distributed over frequency whilst the DFT shows the spectral content of
    your signal, i.e. the amplitude and phase of harmonics in your signal.
    """

    avail_windows = get_ft_windows()

    x_val = np.array(x_val)
    y_val = np.array(y_val)

    # Make a baseline correction to avoid a constant offset near zero
    # frequencies. Offset of the y_val from mean corresponds to half the value
    # at fft_y[0].
    corrected_y = y_val
    if base_corr:
        corrected_y = y_val - y_val.mean()

    ampl_norm_fact = 1.0
    # apply window to data to account for spectral leakage:
    if window in avail_windows:
        window_val = avail_windows[window]['func'](len(y_val))
        corrected_y = corrected_y * window_val
        # to get the correct amplitude in the amplitude spectrum
        ampl_norm_fact = avail_windows[window]['ampl_norm']

    # zeropad for sinc interpolation:
    zeropad_arr = np.zeros(len(corrected_y)*(zeropad_num+1))
    zeropad_arr[:len(corrected_y)] = corrected_y

    # Get the amplitude values from the fourier transformed y values.
    fft_y = np.abs(np.fft.fft(zeropad_arr))

    # Power spectral density (PSD) or just amplitude spectrum of fourier signal:
    power_value = 1.0
    if psd:
        power_value = 2.0

    # The factor 2 accounts for the fact that just the half of the spectrum was
    # taken. The ampl_norm_fact is the normalization factor due to the applied
    # window function (the offset value in the window function):
    fft_y = ((2/len(y_val)) * fft_y * ampl_norm_fact)**power_value

    # Due to the sampling theorem you can only identify frequencies at half
    # of the sample rate, therefore the FT contains an almost symmetric
    # spectrum (the asymmetry results from aliasing effects). Therefore take
    # the half of the values for the display.
    middle = int((len(zeropad_arr)+1)//2)

    # sample spacing of x_axis, if x is a time axis than it corresponds to a
    # timestep:
    x_spacing = np.round(x_val[-1] - x_val[-2], 12)

    # use the helper function of numpy to calculate the x_values for the
    # fourier space. That function will handle an occuring devision by 0:
    fft_x = np.fft.fftfreq(len(zeropad_arr), d=x_spacing)

    return abs(fft_x[:middle]), fft_y[:middle]


################################################################################
#                                                                              #
#                               Defining Sine models                           #
#                                                                              #
################################################################################

##################################################
# Bare sine with unitary amplitude and no offset #
##################################################

def make_baresine_model(self, prefix=None):
    """ Create a bare sine model without amplitude and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params)

    Explanation of the objects:
        object lmfit.model.CompositeModel model:
            A model the lmfit module will use for that fit. Here a
            gaussian model. Returns an object of the class
            lmfit.model.CompositeModel.

        object lmfit.parameter.Parameters params:
            It is basically an OrderedDict, so a dictionary, with keys
            denoting the parameters as string names and values which are
            lmfit.parameter.Parameter (without s) objects, keeping the
            information about the current value.

        For further information have a look in:
    http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
    """

    def bare_sine_function(x, frequency, phase):
        """ Function of a bare sine.

        @param numpy.array x: independant variable - e.g. time
        @param float frequency: frequency
        @param float phase: phase

        @return: reference to method of a sine function in order to use it as a
                 model
        """

        return np.sin(2*np.pi*frequency*x+phase)

    if not isinstance(prefix, str) and prefix is not None:
        self.log.error('The passed prefix <{0}> of type {1} is not a string and'
                       'cannot be used as a prefix and will be ignored for now.'
                       'Correct that!'.format(prefix, type(prefix)))
        model = Model(bare_sine_function, independent_vars=['x'])
    else:
        model = Model(bare_sine_function, independent_vars=['x'], prefix=prefix)

    params = model.make_params()

    return model, params

###############################
# Centred sine with no offset #
###############################


def make_sinewithoutoffset_model(self, prefix=None):
    """ Create a model of sine with an amplitude.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """
    baresine_model, params = self.make_baresine_model(prefix=prefix)
    amplitude_model, params = self.make_amplitude_model(prefix=prefix)

    sine_model = amplitude_model*baresine_model
    params = sine_model.make_params()

    return sine_model, params

############################
# General sine with offset #
############################


def make_sine_model(self, prefix=None):
    """ Create a sine model with amplitude and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    sine_model, params = self.make_sinewithoutoffset_model(prefix=prefix)
    constant_model, params = self.make_constant_model(prefix=prefix)

    sine_offset_model = sine_model + constant_model
    params = sine_offset_model.make_params()

    return sine_offset_model, params

###############################################
# Sinus with exponential decay but not offset #
###############################################


def make_sineexpdecaywithoutoffset_model(self, prefix=None):
    """ Create a model of a sine with exponential decay.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    sine_model, params = self.make_sinewithoutoffset_model(prefix=prefix)
    bareexponentialdecay_model, params = self.make_bareexponentialdecay_model(prefix=prefix)

    sine_exp_decay_model = sine_model*bareexponentialdecay_model
    params = sine_exp_decay_model.make_params()

    return sine_exp_decay_model, params

###################################################
# Sinus with exponential decay and offset fitting #
###################################################

def make_sineexponentialdecay_model(self, prefix=None):
    """ Create a model of a sine with exponential decay and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    sine_exp_decay_model, params = self.make_sineexpdecaywithoutoffset_model(prefix=prefix)
    constant_model, params = self.make_constant_model(prefix=prefix)

    sine_exp_decay_offset_model = sine_exp_decay_model + constant_model
    params = sine_exp_decay_offset_model.make_params()

    return sine_exp_decay_offset_model, params

###################################################
# Sinus with stretched exponential decay fitting  #
###################################################

def make_sinestretchedexponentialdecay_model(self, prefix=None):
    """ Create a model of a sine with stretched exponential decay.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    sine_model, params = self.make_sinewithoutoffset_model(prefix=prefix)
    bare_stretched_exp_decay_model, params = self.make_barestretchedexponentialdecay_model(prefix=prefix)
    constant_model, params = self.make_constant_model(prefix=prefix)

    model = sine_model * bare_stretched_exp_decay_model + constant_model
    params = model.make_params()

    return model, params

###########################################
# Sum of two individual Sinus with offset #
###########################################


def make_sinedouble_model(self, prefix=None):
    """ Create a model of two summed sine with an offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    if prefix is None:
        add_text = ''
    else:
        add_text = prefix

    sine_model1, params = self.make_sinewithoutoffset_model(prefix='s1_'+add_text)
    sine_model2, params = self.make_sinewithoutoffset_model(prefix='s2_'+add_text)

    constant_model, params = self.make_constant_model(prefix=prefix)

    two_sine_offset = sine_model1 + sine_model2 + constant_model
    params = two_sine_offset.make_params()

    return two_sine_offset, params

################################################################################
#    Sum of two individual Sinus with offset and single exponential decay      #
################################################################################


def make_sinedoublewithexpdecay_model(self, prefix=None):
    """ Create a model of two summed sine with an exponential decay and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    if prefix is None:
        add_text = ''
    else:
        add_text = prefix

    sine_model1, params = self.make_sinewithoutoffset_model(prefix='s1_'+add_text)
    sine_model2, params = self.make_sinewithoutoffset_model(prefix='s2_'+add_text)
    bare_exp_decay_model, params = self.make_bareexponentialdecay_model(prefix=prefix)

    constant_model, params = self.make_constant_model(prefix=prefix)

    two_sine_exp_decay_offset = (sine_model1 + sine_model2)*bare_exp_decay_model + constant_model
    params = two_sine_exp_decay_offset.make_params()

    return two_sine_exp_decay_offset, params

###############################################################
# Sum of two individual Sinus exponential decays (and offset) #
###############################################################


def make_sinedoublewithtwoexpdecay_model(self, prefix=None):
    """ Create a model of two summed sine with three exponential decays and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """
    if prefix is None:
        add_text = ''
    else:
        add_text = prefix

    sine_exp_decay_model1, params = self.make_sineexpdecaywithoutoffset_model(prefix='e1_'+add_text)
    sine_exp_decay_model2, params = self.make_sineexpdecaywithoutoffset_model(prefix='e2_'+add_text)

    constant_model, params = self.make_constant_model(prefix=prefix)

    sinedoublewithtwoexpdecay = sine_exp_decay_model1 + sine_exp_decay_model2 + constant_model
    params = sinedoublewithtwoexpdecay.make_params()

    return sinedoublewithtwoexpdecay, params

#############################################
# Sum of three individual Sinus with offset #
#############################################


def make_sinetriple_model(self, prefix=None):
    """ Create a model of three summed sine with an offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    if prefix is None:
        add_text = ''
    else:
        add_text = prefix

    sine_model1, params = self.make_sinewithoutoffset_model(prefix='s1_'+add_text)
    sine_model2, params = self.make_sinewithoutoffset_model(prefix='s2_'+add_text)
    sine_model3, params = self.make_sinewithoutoffset_model(prefix='s3_'+add_text)

    constant_model, params = self.make_constant_model(prefix=prefix)

    three_sine_offset = sine_model1 + sine_model2 + sine_model3 + constant_model
    params = three_sine_offset.make_params()

    return three_sine_offset, params

##########################################################################
# Sum of three individual Sinus with offset and single exponential decay #
##########################################################################


def make_sinetriplewithexpdecay_model(self, prefix=None):
    """ Create a model of three summed sine with an exponential decay and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    if prefix is None:
        add_text = ''
    else:
        add_text = prefix

    sine_model1, params = self.make_sinewithoutoffset_model(prefix='s1_'+add_text)
    sine_model2, params = self.make_sinewithoutoffset_model(prefix='s2_'+add_text)
    sine_model3, params = self.make_sinewithoutoffset_model(prefix='s3_'+add_text)
    bare_exp_decay_model, params = self.make_bareexponentialdecay_model(prefix=prefix)

    constant_model, params = self.make_constant_model(prefix=prefix)

    three_sine_exp_decay_offset = (
        sine_model1 + sine_model2 + sine_model3) * bare_exp_decay_model + constant_model
    params = three_sine_exp_decay_offset.make_params()

    return three_sine_exp_decay_offset, params

#########################################################################
# Sum of three individual Sinus with offset and three exponential decay #
#########################################################################


def make_sinetriplewiththreeexpdecay_model(self, prefix=None):
    """ Create a model of three summed sine with three exponential decays and offset.

    @param str prefix: optional, if multiple models should be used in a
                       composite way and the parameters of each model should be
                       distinguished from each other to prevent name collisions.

    @return tuple: (object model, object params), for more description see in
                   the method make_baresine_model.
    """

    if prefix is None:
        add_text = ''
    else:
        add_text = prefix

    sine_exp_decay_model1, params = self.make_sineexpdecaywithoutoffset_model(prefix='e1_'+add_text)
    sine_exp_decay_model2, params = self.make_sineexpdecaywithoutoffset_model(prefix='e2_'+add_text)
    sine_exp_decay_model3, params = self.make_sineexpdecaywithoutoffset_model(prefix='e3_'+add_text)

    constant_model, params = self.make_constant_model(prefix=prefix)

    three_sine_exp_decay_offset = sine_exp_decay_model1 + sine_exp_decay_model2 + sine_exp_decay_model3 + constant_model
    params = three_sine_exp_decay_offset.make_params()

    return three_sine_exp_decay_offset, params

################################################################################
#                                                                              #
#                        General estimators used later                         #
#                                                                              #
################################################################################


def estimate_baresine(self, x_axis, data, params):
    """ Bare sine estimator with a frequency and phase.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        lmfit.Parameters params: derived OrderedDict object contains the initial
                                 values for the fit.
    """

    # Convert for safety:
    x_axis = np.array(x_axis)
    data = np.array(data)

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # calculate dft with zeropadding to obtain nicer interpolation between the
    # appearing peaks.
    dft_x, dft_y = compute_ft(x_axis, data, zeropad_num=1)

    stepsize = x_axis[1]-x_axis[0]  # for frequency axis
    frequency_max = np.abs(dft_x[np.log(dft_y).argmax()])

    # find minimal distance to the next meas point in the corresponding time value>
    min_x_diff = np.ediff1d(x_axis).min()

    # How many points are used to sample the estimated frequency with min_x_diff:
    iter_steps = int(1/(frequency_max*min_x_diff))
    if iter_steps < 1:
        iter_steps = 1

    sum_res = np.zeros(iter_steps)

    # Procedure: Create sin waves with different phases and perform a summation.
    #            The sum shows how well the sine was fitting to the actual data.
    #            The best fitting sine should be a maximum of the summed time
    #            trace.

    for iter_s in range(iter_steps):
        func_val = np.sin(2*np.pi*frequency_max*x_axis + iter_s/iter_steps *2*np.pi)
        sum_res[iter_s] = np.abs(data - func_val).sum()

    # The minimum indicates where the sine function was fittng the worst,
    # therefore subtract pi. This will also ensure that the estimated phase will
    # be in the interval [-pi,pi].
    phase = sum_res.argmax()/iter_steps *2*np.pi - np.pi

    params['frequency'].set(value=frequency_max, min=0.0, max=1/stepsize*3)
    params['phase'].set(value=phase, min=-np.pi, max=np.pi)

    return error, params


def estimate_sinewithoutoffset(self, x_axis, data, params):
    """ Sine estimator, with an amplitude, frequency and phase.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        lmfit.Parameters params: derived OrderedDict object contains the initial
                                 values for the fit.
    """

    # Convert for safety:
    x_axis = np.array(x_axis)
    data = np.array(data)

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # sort the input
    sorted_indices = x_axis.argsort()
    x_axis = x_axis[sorted_indices]
    data = data[sorted_indices]

    # estimate amplitude
    ampl_val = max(np.abs(data.min()), np.abs(data.max()))

    # calculate dft with zeropadding to obtain nicer interpolation between the
    # appearing peaks.
    dft_x, dft_y = compute_ft(x_axis, data, zeropad_num=1)

    stepsize = x_axis[1] - x_axis[0]  # for frequency axis

    # remove the zero values so that it is still possible to take
    # the logarithm. The logarithm acts as a non linear filter
    # which decrease the noise in the dft and enhances the
    # prominent frequencies.
    indicies = np.where(dft_y > 0.0)

    dft_x_red = dft_x[indicies]
    dft_y_red = dft_y[indicies]

    frequency_max = np.abs(dft_x_red[np.log(dft_y_red).argmax()])

    # find minimal distance to the next meas point in the corresponding time value>
    diff_array = np.ediff1d(x_axis)
    min_x_diff = diff_array.min()

    # if at least two identical values are in the array, then the difference is of course zero,
    # catch that case.
    for tries, diff_array_step in enumerate(diff_array):
        if np.isclose(min_x_diff, 0.0, atol=1e-12):
            index = np.argmin(diff_array)
            diff_array = np.delete(diff_array, index)
            min_x_diff = diff_array.min()

        else:
            if len(diff_array) == 0:
                self.log.error(
                    'The passed x_axis for the sinus estimation contains the same values!'
                    ' Cannot do the fit!')

                return -1, params
            else:
                min_x_diff = diff_array.min()
            break

    # How many points are used to sample the estimated frequency with min_x_diff:
    iter_steps = int(1/(frequency_max*min_x_diff))
    if iter_steps < 1:
        iter_steps = 1

    sum_res = np.zeros(iter_steps)

    # Procedure: Create sin waves with different phases and perform a summation.
    #            The sum shows how well the sine was fitting to the actual data.
    #            The best fitting sine should be a maximum of the summed time
    #            trace.

    for iter_s in range(iter_steps):
        func_val = ampl_val * np.sin(2*np.pi*frequency_max*x_axis + iter_s/iter_steps*2*np.pi)
        sum_res[iter_s] = np.abs(data - func_val).sum()

    # The minimum indicates where the sine function was fitting the worst,
    # therefore subtract pi. This will also ensure that the estimated phase will
    # be in the interval [-pi,pi].
    phase = sum_res.argmax()/iter_steps *2*np.pi - np.pi

    # values and bounds of initial parameters
    params['amplitude'].set(value=ampl_val)
    params['frequency'].set(value=frequency_max, min=0.0, max=1/stepsize*3)
    params['phase'].set(value=phase, min=-np.pi, max=np.pi)

    return error, params


################################################################################
#                                                                              #
#              Fitting methods and their estimators                            #
#                                                                              #
################################################################################

########
# Sine #
########

def make_sine_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a sine fit with a constant offset on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """

    sine, params = self.make_sine_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = sine.fit(data, x=x_axis, params=params, **kwargs)
    except:
        result = sine.fit(data, x=x_axis, params=params, **kwargs)
        self.log.error('The sine fit did not work.\n'
                       'Error message: {0}\n'.format(result.message))

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()

    period = 1 / result.params['frequency'].value
    try:
        period_err = result.params['frequency'].stderr / (result.params['frequency'])**2
    except ZeroDivisionError:
        period_err = np.inf

    result_str_dict['Period'] = {'value': period if period else 0.0,
                                 'error': period_err if period_err else 0.0,
                                 'unit': units[0]}

    result_str_dict['Frequency'] = {'value': result.params['frequency'].value,
                                    'error': result.params['frequency'].stderr,
                                    'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Phase'] = {'value': 180/np.pi*result.params['phase'].value,
                                'error': 180/np.pi*result.params['phase'].stderr,
                                'unit': 'deg'}

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result_str_dict['Amplitude'] = {'value': result.params['amplitude'].value,
                                    'error':  result.params['amplitude'].stderr,
                                    'unit': units[1]}

    result_str_dict['Contrast'] = {'value': ((2*result.params['amplitude'].value) /
                                             (result.params['offset'].value+result.params['amplitude'].value)*100),
                                   'error':  (np.abs((2*result.params['amplitude'].value) /
                                              (result.params['offset'].value+result.params['amplitude'].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params['amplitude'].value) + (2*result.params['amplitude'].value) /
                                             (result.params['offset'].value + result.params['amplitude'].value)**2) *
                                             result.params['amplitude'].stderr))*100,
                                   'unit': '%'}

    result.result_str_dict = result_str_dict
    return result


def estimate_sine(self, x_axis, data, params):
    """ Provides an estimator to obtain initial values for sine fitting.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # set the offset as the average of the data
    offset = np.average(data)

    # level data
    data_level = data - offset

    error, params = self.estimate_sinewithoutoffset(x_axis=x_axis, data=data_level, params=params)

    params['offset'].set(value=offset)

    return error, params

##########################
# Sine exponential decay #
##########################


def make_sineexponentialdecay_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a sine exponential decay fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    sine_exp_decay_offset, params = self.make_sineexponentialdecay_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = sine_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)
    except:

        result = sine_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)
        self.log.error('The sineexponentialdecayoffset fit did not work.\n'
                       'Error message: {0}'.format(result.message))

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()

    period = 1/result.params['frequency'].value
    try:
        period_err = result.params['frequency'].stderr / (result.params['frequency'])**2
    except ZeroDivisionError:
        period_err = np.inf

    result_str_dict['Period'] = {'value': period if period else 0.0,
                                 'error': period_err if period_err else 0.0,
                                 'unit': units[0]}

    result_str_dict['Frequency'] = {'value': result.params['frequency'].value,
                                    'error': result.params['frequency'].stderr,
                                    'unit': 'Hz' if units[0] == 's' else '1/'+units[0]}

    result_str_dict['Amplitude'] = {'value': result.params['amplitude'].value,
                                    'error': result.params['amplitude'].stderr,
                                    'unit': units[1]}

    result_str_dict['Contrast'] = {'value': ((2*result.params['amplitude'].value) /
                                             (result.params['offset'].value+result.params['amplitude'].value)*100),
                                   'error':  (np.abs((2*result.params['amplitude'].value) /
                                              (result.params['offset'].value+result.params['amplitude'].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params['amplitude'].value) + (2*result.params['amplitude'].value) /
                                             (result.params['offset'].value + result.params['amplitude'].value)**2) *
                                             result.params['amplitude'].stderr))*100,
                                   'unit': '%'}

    result_str_dict['Phase'] = {'value': 180/np.pi*result.params['phase'].value,
                                'error': 180/np.pi*result.params['phase'].stderr,
                                'unit': 'deg'}

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result_str_dict['Lifetime'] = {'value': result.params['lifetime'].value,
                                   'error': result.params['lifetime'].stderr,
                                   'unit': units[0]}

    result_str_dict['Beta'] = {'value': result.params['beta'].value,
                               'error': result.params['beta'].stderr,
                               'unit': ''}

    result.result_str_dict = result_str_dict
    return result


def estimate_sineexponentialdecay(self, x_axis, data, params=None):
    """ Provide an estimator to obtain initial values for a sine exponential
        decay with offset function.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    # Convert for safety:
    x_axis = np.array(x_axis)
    data = np.array(data)

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # set the offset as the mean of the data
    offset = np.mean(data)

    # level data
    data_level = data - offset

    # estimate amplitude
    ampl_val = max(np.abs(data_level.min()), np.abs(data_level.max()))

    dft_x, dft_y = compute_ft(x_axis, data_level, zeropad_num=1)

    stepsize = x_axis[1] - x_axis[0]  # for frequency axis

    frequency_max = np.abs(dft_x[dft_y.argmax()])

    # remove noise
    a = np.std(dft_y)
    for i in range(0, len(dft_x)):
        if dft_y[i] <= a:
            dft_y[i] = 0

    # calculating the width of the FT peak for the estimation of lifetime
    s = 0
    for i in range(0, len(dft_x)):
        s += dft_y[i]*abs(dft_x[1]-dft_x[0])/max(dft_y)
    lifetime_val = 0.5/s

    # find minimal distance to the next meas point in the corresponding x value
    min_x_diff = np.ediff1d(x_axis).min()

    # How many points are used to sample the estimated frequency with min_x_diff:
    iter_steps = int(1/(frequency_max*min_x_diff))
    if iter_steps < 1:
        iter_steps = 1

    sum_res = np.zeros(iter_steps)

    # Procedure: Create sin waves with different phases and perform a summation.
    #            The sum shows how well the sine was fitting to the actual data.
    #            The best fitting sine should be a maximum of the summed time
    #            trace.

    for iter_s in range(iter_steps):
        func_val = ampl_val * np.sin(2*np.pi*frequency_max*x_axis + iter_s/iter_steps *2*np.pi)
        sum_res[iter_s] = np.abs(data_level - func_val).sum()

    # The minimum indicates where the sine function was fittng the worst,
    # therefore subtract pi. This will also ensure that the estimated phase will
    # be in the interval [-pi,pi].
    phase = (sum_res.argmax()/iter_steps *2*np.pi - np.pi)%(2*np.pi)

    # values and bounds of initial parameters
    params['frequency'].set(value=frequency_max,
                            min=min(0.1 / (x_axis[-1]-x_axis[0]), dft_x[3]),
                            max=min(0.5 / stepsize, dft_x.max()-abs(dft_x[2]-dft_x[0])))
    params['phase'].set(value=phase, min=-2*np.pi, max=2*np.pi)
    params['amplitude'].set(value=ampl_val, min=0)
    params['offset'].set(value=offset)

    params['lifetime'].set(value=lifetime_val,
                           min=2*(x_axis[1]-x_axis[0]),
                           max=1/(abs(dft_x[1]-dft_x[0])*0.5))

    return error, params

###################################################
# Sinus with stretched exponential decay fitting  #
###################################################


def make_sinestretchedexponentialdecay_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a sine stretched exponential decay fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    sine_stretched_exp_decay, params = self.make_sinestretchedexponentialdecay_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = sine_stretched_exp_decay.fit(data, x=x_axis, params=params, **kwargs)
    except:
        result = sine_stretched_exp_decay.fit(data, x=x_axis, params=params, **kwargs)
        self.log.error('The sineexponentialdecay fit did not work.\n'
                       'Error message: {0}'.format(result.message))

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()

    period = 1 / result.params['frequency'].value
    try:
        period_err = result.params['frequency'].stderr / (result.params['frequency'])**2
    except ZeroDivisionError:
        period_err = np.inf

    result_str_dict['Period'] = {'value': period if period else 0.0,
                                 'error': period_err if period_err else 0.0,
                                 'unit': units[0]}

    result_str_dict['Frequency'] = {'value': result.params['frequency'].value,
                                    'error': result.params['frequency'].stderr,
                                    'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Amplitude'] = {'value': result.params['amplitude'].value,
                                    'error': result.params['amplitude'].stderr,
                                    'unit': units[1]}

    result_str_dict['Contrast'] = {'value': ((2*result.params['amplitude'].value) /
                                             (result.params['offset'].value+result.params['amplitude'].value)*100),
                                   'error':  (np.abs((2*result.params['amplitude'].value) /
                                              (result.params['offset'].value+result.params['amplitude'].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params['amplitude'].value) + (2*result.params['amplitude'].value) /
                                             (result.params['offset'].value + result.params['amplitude'].value)**2) *
                                             result.params['amplitude'].stderr))*100,
                                   'unit': '%'}

    result_str_dict['Phase'] = {'value': 180/np.pi*result.params['phase'].value,
                                'error': 180/np.pi*result.params['phase'].stderr,
                                'unit': 'deg'}

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result_str_dict['Lifetime'] = {'value': result.params['lifetime'].value,
                                   'error': result.params['lifetime'].stderr,
                                   'unit': units[0]}

    result_str_dict['Beta'] = {'value': result.params['beta'].value,
                               'error': result.params['beta'].stderr,
                               'unit': ''}

    result.result_str_dict = result_str_dict
    return result


def estimate_sinestretchedexponentialdecay(self, x_axis, data, params):
    """ Provide a estimation of a initial values for a sine stretched exponential decay function.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param Parameters object params: object includes parameter dictionary which can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error, params = self.estimate_sineexponentialdecay(x_axis, data, params)
    #TODO: estimate the exponent cleaverly! For now, set the initial value to 2
    #      since the usual values for our cases are between 1 and 3.
    params['beta'].set(value=2, min=0.0, max=10)

    return error, params

###########################################
# Sum of two individual Sinus with offset #
###########################################


def make_sinedouble_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a two sine with offset fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    two_sine_offset, params = self.make_sinedouble_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = two_sine_offset.fit(data, x=x_axis, params=params, **kwargs)
    except:
        self.log.warning('The twosineexpdecayoffset fit did not work. '
                         'Error message: {}'.format(str(result.message)))
        result = two_sine_offset.fit(data, x=x_axis, params=params, **kwargs)

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()  # create result string for gui or OrderedDict()

    period1 = 1 / result.params['s1_frequency'].value
    try:
        period1_err = result.params['s1_frequency'].stderr / (result.params['s1_frequency'])**2
    except ZeroDivisionError:
        period1_err = np.inf

    period2 = 1 / result.params['s2_frequency'].value
    try:
        period2_err = result.params['s2_frequency'].stderr / (result.params['s2_frequency'])**2
    except ZeroDivisionError:
        period2_err = np.inf

    result_str_dict['Period 1'] = {'value': period1 if period1 else 0.0,
                                   'error': period1_err if period1_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Period 2'] = {'value': period2 if period2 else 0.0,
                                   'error': period2_err if period2_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Frequency 1'] = {'value': result.params['s1_frequency'].value,
                                      'error': result.params['s1_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Frequency 2'] = {'value': result.params['s2_frequency'].value,
                                      'error': result.params['s2_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Amplitude 1'] = {'value': result.params['s1_amplitude'].value,
                                      'error': result.params['s1_amplitude'].stderr,
                                      'unit': units[1]}

    result_str_dict['Amplitude 2'] = {'value': result.params['s2_amplitude'].value,
                                      'error': result.params['s2_amplitude'].stderr,
                                      'unit': units[1]}

    amp_string = 's1_amplitude'
    result_str_dict['Contrast 1'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                    'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                   'unit': '%'}

    amp_string = 's2_amplitude'
    result_str_dict['Contrast 2'] = {'value': ((2*result.params[amp_string].value) /
                                             (result.params['offset'].value+result.params[amp_string].value)*100),
                                   'error':  (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                             (result.params['offset'].value + result.params[amp_string].value)**2) *
                                             result.params[amp_string].stderr))*100,
                                   'unit': '%'}

    result_str_dict['Phase 1'] = {'value': 180/np.pi*result.params['s1_phase'].value,
                                  'error': 180/np.pi*result.params['s1_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Phase 2'] = {'value': 180/np.pi*result.params['s2_phase'].value,
                                  'error': 180/np.pi*result.params['s2_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result.result_str_dict = result_str_dict
    return result


def estimate_sinedouble(self, x_axis, data, params):
    """ Provides an estimator for initial values of two sines with offset fitting.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # That procedure seems to work extremely reliable: make two consecutive
    # sine offset fits where for the second the first fit is subtracted to
    # delete the first sine in the data.

    result1 = self.make_sine_fit(x_axis=x_axis, data=data, estimator=self.estimate_sine)
    data_sub = data - result1.best_fit

    result2 = self.make_sine_fit(x_axis=x_axis, data=data_sub, estimator=self.estimate_sine)

    # Fill the parameter dict:
    params['s1_amplitude'].set(value=result1.params['amplitude'].value)
    params['s1_frequency'].set(value=result1.params['frequency'].value)
    params['s1_phase'].set(value=result1.params['phase'].value)

    params['s2_amplitude'].set(value=result2.params['amplitude'].value)
    params['s2_frequency'].set(value=result2.params['frequency'].value)
    params['s2_phase'].set(value=result2.params['phase'].value)

    params['offset'].set(value=data.mean())

    return error, params

################################################################################
#    Sum of two individual Sinus with offset and single exponential decay      #
################################################################################


def make_sinedoublewithexpdecay_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a two sine with one exponential decay offset fit on the provided
        data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    two_sine_exp_decay_offset, params = self.make_sinedoublewithexpdecay_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = two_sine_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)
    except:
        self.log.warning('The sinedoublewithexpdecay fit did not work. '
                         'Error message: {}'.format(str(result.message)))
        result = two_sine_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()  # create result string for gui or OrderedDict()

    period1 = 1 / result.params['s1_frequency'].value
    try:
        period1_err = result.params['s1_frequency'].stderr / (result.params['s1_frequency']) ** 2
    except ZeroDivisionError:
        period1_err = np.inf

    period2 = 1 / result.params['s2_frequency'].value
    try:
        period2_err = result.params['s2_frequency'].stderr / (result.params['s2_frequency']) ** 2
    except ZeroDivisionError:
        period2_err = np.inf

    result_str_dict['Period 1'] = {'value': period1 if period1 else 0.0,
                                   'error': period1_err if period1_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Period 2'] = {'value': period2 if period2 else 0.0,
                                   'error': period2_err if period2_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Frequency 1'] = {'value': result.params['s1_frequency'].value,
                                      'error': result.params['s1_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Frequency 2'] = {'value': result.params['s2_frequency'].value,
                                      'error': result.params['s2_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Amplitude 1'] = {'value': result.params['s1_amplitude'].value,
                                      'error': result.params['s1_amplitude'].stderr,
                                      'unit': units[1]}

    result_str_dict['Amplitude 2'] = {'value': result.params['s2_amplitude'].value,
                                      'error': result.params['s2_amplitude'].stderr,
                                      'unit': units[1]}

    amp_string = 's1_amplitude'
    result_str_dict['Contrast 1'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    amp_string = 's2_amplitude'
    result_str_dict['Contrast 2'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    result_str_dict['Phase 1'] = {'value': 180/np.pi*result.params['s1_phase'].value,
                                  'error': 180/np.pi*result.params['s1_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Phase 2'] = {'value': 180/np.pi*result.params['s2_phase'].value,
                                  'error': 180/np.pi*result.params['s2_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result_str_dict['Lifetime'] = {'value': result.params['lifetime'].value,
                                   'error': result.params['lifetime'].stderr,
                                   'unit': units[0]}

    result.result_str_dict = result_str_dict
    return result


def estimate_sinedoublewithexpdecay(self, x_axis, data, params):
    """ Provides an estimator for initial values of two sine with offset and
        exponential decay fitting.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # That procedure seems to work extremely reliable: make two consecutive
    # sine offset fits where for the second the first fit is subtracted to
    # delete the first sine in the data.

    result1 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data,
        estimator=self.estimate_sineexponentialdecay)
    data_sub = data - result1.best_fit

    result2 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data_sub,
        estimator=self.estimate_sineexponentialdecay)

    # Fill the parameter dict:
    params['s1_amplitude'].set(value=result1.params['amplitude'].value)
    params['s1_frequency'].set(value=result1.params['frequency'].value)
    params['s1_phase'].set(value=result1.params['phase'].value)

    params['s2_amplitude'].set(value=result2.params['amplitude'].value)
    params['s2_frequency'].set(value=result2.params['frequency'].value)
    params['s2_phase'].set(value=result2.params['phase'].value)

    lifetime = (result1.params['lifetime'].value + result2.params['lifetime'].value)/2
    params['lifetime'].set(value=lifetime, min=2*(x_axis[1]-x_axis[0]))
    params['offset'].set(value=data.mean())

    return error, params


###############################################################
# Sum of two individual Sinus exponential decays (and offset) #
###############################################################
# Problem with stderr: x.stderr will always be 0 for this model!


def make_sinedoublewithtwoexpdecay_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a two sine with two exponential decay and offset fit on the
        provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    two_sine_two_exp_decay_offset, params = self.make_sinedoublewithtwoexpdecay_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = two_sine_two_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)
    except:
        self.log.warning('The sinedoublewithtwoexpdecay fit did not work. '
                         'Error message: {}'.format(str(result.message)))
        result = two_sine_two_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()  # create result string for gui or OrderedDict()

    period1 = 1 / result.params['e1_frequency'].value
    try:
        period1_err = result.params['e1_frequency'].stderr / (result.params['e1_frequency']) ** 2
    except ZeroDivisionError:
        period1_err = np.inf

    period2 = 1 / result.params['e2_frequency'].value
    try:
        period2_err = result.params['e2_frequency'].stderr / (result.params['e2_frequency']) ** 2
    except ZeroDivisionError:
        period2_err = np.inf

    result_str_dict['Period 1'] = {'value': period1 if period1 else 0.0,
                                   'error': period1_err if period1_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Period 2'] = {'value': period2 if period2 else 0.0,
                                   'error': period2_err if period2_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Frequency 1'] = {'value': result.params['e1_frequency'].value,
                                      'error': result.params['e1_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Frequency 2'] = {'value': result.params['e2_frequency'].value,
                                      'error': result.params['e2_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Amplitude 1'] = {'value': result.params['e1_amplitude'].value,
                                      'error': result.params['e1_amplitude'].stderr,
                                      'unit': units[1]}

    result_str_dict['Amplitude 2'] = {'value': result.params['e2_amplitude'].value,
                                      'error': result.params['e2_amplitude'].stderr,
                                      'unit': units[1]}

    amp_string = 'e1_amplitude'
    result_str_dict['Contrast 1'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    amp_string = 'e2_amplitude'
    result_str_dict['Contrast 2'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    result_str_dict['Phase 1'] = {'value': 180/np.pi*result.params['e1_phase'].value,
                                  'error': 180/np.pi*result.params['e1_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Phase 2'] = {'value': 180/np.pi*result.params['e2_phase'].value,
                                  'error': 180/np.pi*result.params['e2_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Lifetime 1'] = {'value': result.params['e1_lifetime'].value,
                                     'error': result.params['e1_lifetime'].stderr,
                                     'unit': units[0]}

    result_str_dict['Lifetime 2'] = {'value': result.params['e2_lifetime'].value,
                                     'error': result.params['e2_lifetime'].stderr,
                                     'unit': units[0]}

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result.result_str_dict = result_str_dict
    return result


def estimate_sinedoublewithtwoexpdecay(self, x_axis, data, params):
    """ Provides an estimator for initial values of two sine with offset and
        two exponential decay fitting.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # That procedure seems to work extremely reliable: make two consecutive
    # sine offset fits where for the second the first fit is subtracted to
    # delete the first sine in the data.

    result1 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data,
        estimator=self.estimate_sineexponentialdecay)
    data_sub = data - result1.best_fit

    result2 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data_sub,
        estimator=self.estimate_sineexponentialdecay)

    # Fill the parameter dict:
    params['e1_amplitude'].set(value=result1.params['amplitude'].value)
    params['e1_frequency'].set(value=result1.params['frequency'].value)
    params['e1_phase'].set(value=result1.params['phase'].value)
    params['e1_lifetime'].set(value=result1.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))

    params['e2_amplitude'].set(value=result2.params['amplitude'].value)
    params['e2_frequency'].set(value=result2.params['frequency'].value)
    params['e2_phase'].set(value=result2.params['phase'].value)
    params['e2_lifetime'].set(value=result2.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))

    params['offset'].set(value=data.mean())

    return error, params

#############################################
# Sum of three individual Sinus with offset #
#############################################


def make_sinetriple_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a three sine with offset fit on the provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    two_sine_offset, params = self.make_sinetriple_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = two_sine_offset.fit(data, x=x_axis, params=params, **kwargs)
    except:
        self.log.warning('The threesineexpdecayoffset fit did not work. '
                         'Error message: {}'.format(str(result.message)))
        result = two_sine_offset.fit(data, x=x_axis, params=params, **kwargs)

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()  # create result string for gui or OrderedDict()

    period1 = 1 / result.params['s1_frequency'].value
    try:
        period1_err = result.params['s1_frequency'].stderr / (result.params['s1_frequency']) ** 2
    except ZeroDivisionError:
        period1_err = np.inf

    period2 = 1 / result.params['s2_frequency'].value
    try:
        period2_err = result.params['s2_frequency'].stderr / (result.params['s2_frequency']) ** 2
    except ZeroDivisionError:
        period2_err = np.inf

    period3 = 1 / result.params['s3_frequency'].value
    try:
        period3_err = result.params['s3_frequency'].stderr / (result.params['s3_frequency']) ** 2
    except ZeroDivisionError:
        period3_err = np.inf

    result_str_dict['Period 1'] = {'value': period1 if period1 else 0.0,
                                   'error': period1_err if period1_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Period 2'] = {'value': period2 if period2 else 0.0,
                                   'error': period2_err if period2_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Period 3'] = {'value': period3 if period3 else 0.0,
                                   'error': period3_err if period3_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Frequency 1'] = {'value': result.params['s1_frequency'].value,
                                      'error': result.params['s1_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Frequency 2'] = {'value': result.params['s2_frequency'].value,
                                      'error': result.params['s2_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Frequency 3'] = {'value': result.params['s3_frequency'].value,
                                      'error': result.params['s3_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Amplitude 1'] = {'value': result.params['s1_amplitude'].value,
                                      'error': result.params['s1_amplitude'].stderr,
                                      'unit': units[1]}

    result_str_dict['Amplitude 2'] = {'value': result.params['s2_amplitude'].value,
                                      'error': result.params['s2_amplitude'].stderr,
                                      'unit': units[1]}

    result_str_dict['Amplitude 3'] = {'value': result.params['s3_amplitude'].value,
                                      'error': result.params['s3_amplitude'].stderr,
                                      'unit': units[1]}

    amp_string = 's1_amplitude'
    result_str_dict['Contrast 1'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    amp_string = 's2_amplitude'
    result_str_dict['Contrast 2'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    amp_string = 's3_amplitude'
    result_str_dict['Contrast 3'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    result_str_dict['Phase 1'] = {'value': 180/np.pi*result.params['s1_phase'].value,
                                  'error': 180/np.pi*result.params['s1_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Phase 2'] = {'value': 180/np.pi*result.params['s2_phase'].value,
                                  'error': 180/np.pi*result.params['s2_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Phase 3'] = {'value': 180/np.pi*result.params['s3_phase'].value,
                                  'error': 180/np.pi*result.params['s3_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result.result_str_dict = result_str_dict
    return result


def estimate_sinetriple(self, x_axis, data, params):
    """ Provides an estimator for initial values of three sines with offset fitting.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # That procedure seems to work extremely reliable: make three consecutive
    # sine offset fits where for the next fit the previous is subtracted to
    # delete its contribution in the data.

    res1 = self.make_sine_fit(x_axis=x_axis, data=data, estimator=self.estimate_sine)
    data_sub1 = data - res1.best_fit

    res2 = self.make_sine_fit(x_axis=x_axis, data=data_sub1, estimator=self.estimate_sine)
    data_sub2 = data_sub1 - res2.best_fit

    res3 = self.make_sine_fit(x_axis=x_axis, data=data_sub2, estimator=self.estimate_sine)

    # Fill the parameter dict:
    params['s1_amplitude'].set(value=res1.params['amplitude'].value)
    params['s1_frequency'].set(value=res1.params['frequency'].value)
    params['s1_phase'].set(value=res1.params['phase'].value)

    params['s2_amplitude'].set(value=res2.params['amplitude'].value)
    params['s2_frequency'].set(value=res2.params['frequency'].value)
    params['s2_phase'].set(value=res2.params['phase'].value)

    params['s3_amplitude'].set(value=res3.params['amplitude'].value)
    params['s3_frequency'].set(value=res3.params['frequency'].value)
    params['s3_phase'].set(value=res3.params['phase'].value)

    params['offset'].set(value=data.mean())

    return error, params

##########################################################################
# Sum of three individual Sinus with offset and single exponential decay #
##########################################################################


def make_sinetriplewithexpdecay_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a three sine with one exponential decay offset fit on the provided
        data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    three_sine_exp_decay_offset, params = self.make_sinetriplewithexpdecay_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params, update_params=add_params)
    try:
        result = three_sine_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)
    except:
        self.log.warning('The sinetriplewithexpdecay fit did not work. '
                         'Error message: {}'.format(str(result.message)))
        result = three_sine_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()  # create result string for gui or OrderedDict()

    period1 = 1 / result.params['s1_frequency'].value
    try:
        period1_err = result.params['s1_frequency'].stderr / (result.params['s1_frequency']) ** 2
    except ZeroDivisionError:
        period1_err = np.inf

    period2 = 1 / result.params['s2_frequency'].value
    try:
        period2_err = result.params['s2_frequency'].stderr / (result.params['s2_frequency']) ** 2
    except ZeroDivisionError:
        period2_err = np.inf

    period3 = 1 / result.params['s3_frequency'].value
    try:
        period3_err = result.params['s3_frequency'].stderr / (result.params['s3_frequency']) ** 2
    except ZeroDivisionError:
        period3_err = np.inf

    result_str_dict['Period 1'] = {'value': period1 if period1 else 0.0,
                                   'error': period1_err if period1_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Period 2'] = {'value': period2 if period2 else 0.0,
                                   'error': period2_err if period2_err else 0.0,
                                   'unit': units[0]}
    result_str_dict['Period 3'] = {'value': period3 if period3 else 0.0,
                                   'error': period3_err if period3_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Frequency 1'] = {'value': result.params['s1_frequency'].value,
                                      'error': result.params['s1_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Frequency 2'] = {'value': result.params['s2_frequency'].value,
                                      'error': result.params['s2_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Frequency 3'] = {'value': result.params['s3_frequency'].value,
                                      'error': result.params['s3_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Amplitude 1'] = {'value': result.params['s1_amplitude'].value,
                                      'error': result.params['s1_amplitude'].stderr,
                                      'unit': units[1]}

    result_str_dict['Amplitude 2'] = {'value': result.params['s2_amplitude'].value,
                                      'error': result.params['s2_amplitude'].stderr,
                                      'unit': units[1]}

    result_str_dict['Amplitude 3'] = {'value': result.params['s3_amplitude'].value,
                                      'error': result.params['s3_amplitude'].stderr,
                                      'unit': units[1]}


    amp_string = 's1_amplitude'
    result_str_dict['Contrast 1'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    amp_string = 's2_amplitude'
    result_str_dict['Contrast 2'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    amp_string = 's3_amplitude'
    result_str_dict['Contrast 3'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    result_str_dict['Phase 1'] = {'value': 180/np.pi*result.params['s1_phase'].value,
                                  'error': 180/np.pi*result.params['s1_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Phase 2'] = {'value': 180/np.pi*result.params['s2_phase'].value,
                                  'error': 180/np.pi*result.params['s2_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Phase 3'] = {'value': 180/np.pi*result.params['s3_phase'].value,
                                  'error': 180/np.pi*result.params['s3_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Lifetime'] = {'value': result.params['lifetime'].value,
                                   'error': result.params['lifetime'].stderr,
                                   'unit': units[0]}

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result.result_str_dict = result_str_dict
    return result


def estimate_sinetriplewithexpdecay(self, x_axis, data, params):
    """ Provides an estimator for initial values of three sine with offset and
        exponential decay fitting.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # That procedure seems to work extremely reliable: make three consecutive
    # sine exponential decay with offset fits where for the next fit the
    # previous is subtracted to delete its contribution in the data.

    res1 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data,
        estimator=self.estimate_sineexponentialdecay)

    data_sub1 = data - res1.best_fit

    res2 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data_sub1,
        estimator=self.estimate_sineexponentialdecay)

    data_sub2 = data_sub1 - res2.best_fit

    res3 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data_sub2,
        estimator=self.estimate_sineexponentialdecay)

    # Fill the parameter dict:
    params['s1_amplitude'].set(value=res1.params['amplitude'].value)
    params['s1_frequency'].set(value=res1.params['frequency'].value)
    params['s1_phase'].set(value=res1.params['phase'].value)

    params['s2_amplitude'].set(value=res2.params['amplitude'].value)
    params['s2_frequency'].set(value=res2.params['frequency'].value)
    params['s2_phase'].set(value=res2.params['phase'].value)

    params['s3_amplitude'].set(value=res3.params['amplitude'].value)
    params['s3_frequency'].set(value=res3.params['frequency'].value)
    params['s3_phase'].set(value=res3.params['phase'].value)

    lifetime = (res1.params['lifetime'].value + res2.params['lifetime'].value + res3.params['lifetime'].value)/3
    params['lifetime'].set(value=lifetime,
                           min=2*(x_axis[1]-x_axis[0]))
    params['offset'].set(value=data.mean())

    return error, params

#########################################################################
# Sum of three individual Sinus with offset and three exponential decay #
#########################################################################


def make_sinetriplewiththreeexpdecay_fit(self, x_axis, data, estimator, units=None, add_params=None, **kwargs):
    """ Perform a three sine with three exponential decay and offset fit on the
        provided data.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param method estimator: Pointer to the estimator method
    @param list units: List containing the ['horizontal', 'vertical'] units as strings
    @param Parameters or dict add_params: optional, additional parameters of
                type lmfit.parameter.Parameters, OrderedDict or dict for the fit
                which will be used instead of the values from the estimator.

    @return object result: lmfit.model.ModelFit object, all parameters
                           provided about the fitting, like: success,
                           initial fitting values, best fitting values, data
                           with best fit with given axis,...
    """
    three_sine_three_exp_decay_offset, params = self.make_sinetriplewiththreeexpdecay_model()

    error, params = estimator(x_axis, data, params)

    params = self._substitute_params(initial_params=params,
                                     update_params=add_params)
    try:
        result = three_sine_three_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)
    except:
        self.log.warning('The twosinetwoexpdecayoffset fit did not work. '
                         'Error message: {}'.format(str(result.message)))
        result = three_sine_three_exp_decay_offset.fit(data, x=x_axis, params=params, **kwargs)

    if units is None:
        units = ['arb. unit', 'arb. unit']

    result_str_dict = dict()  # create result string for gui or OrderedDict()

    period1 = 1 / result.params['e1_frequency'].value
    try:
        period1_err = result.params['e1_frequency'].stderr / (result.params['e1_frequency']) ** 2
    except ZeroDivisionError:
        period1_err = np.inf

    period2 = 1 / result.params['e2_frequency'].value
    try:
        period2_err = result.params['e2_frequency'].stderr / (result.params['e2_frequency']) ** 2
    except ZeroDivisionError:
        period2_err = np.inf

    period3 = 1 / result.params['e3_frequency'].value
    try:
        period3_err = result.params['e3_frequency'].stderr / (result.params['e3_frequency']) ** 2
    except ZeroDivisionError:
        period3_err = np.inf

    result_str_dict['Period 1'] = {'value': period1 if period1 else 0.0,
                                   'error': period1_err if period1_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Period 2'] = {'value': period2 if period2 else 0.0,
                                   'error': period2_err if period2_err else 0.0,
                                   'unit': units[0]}
    result_str_dict['Period 3'] = {'value': period3 if period3 else 0.0,
                                   'error': period3_err if period3_err else 0.0,
                                   'unit': units[0]}

    result_str_dict['Frequency 1'] = {'value': result.params['e1_frequency'].value,
                                      'error': result.params['e1_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Frequency 2'] = {'value': result.params['e2_frequency'].value,
                                      'error': result.params['e2_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Frequency 3'] = {'value': result.params['e3_frequency'].value,
                                      'error': result.params['e3_frequency'].stderr,
                                      'unit': 'Hz' if units[0] == 's' else '1/' + units[0]}

    result_str_dict['Amplitude 1'] = {'value': result.params['e1_amplitude'].value,
                                      'error': result.params['e1_amplitude'].stderr,
                                      'unit': units[1]}

    result_str_dict['Amplitude 2'] = {'value': result.params['e2_amplitude'].value,
                                      'error': result.params['e2_amplitude'].stderr,
                                      'unit': units[1]}

    result_str_dict['Amplitude 3'] = {'value': result.params['e3_amplitude'].value,
                                      'error': result.params['e3_amplitude'].stderr,
                                      'unit': units[1]}

    amp_string = 'e1_amplitude'
    result_str_dict['Contrast 1'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    amp_string = 'e2_amplitude'
    result_str_dict['Contrast 2'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}

    amp_string = 'e3_amplitude'
    result_str_dict['Contrast 3'] = {'value': ((2*result.params[amp_string].value) /
                                               (result.params['offset'].value+result.params[amp_string].value)*100),
                                     'error': (np.abs((2*result.params[amp_string].value) /
                                              (result.params['offset'].value+result.params[amp_string].value)**2 *
                                             result.params['offset'].stderr) +
                                             np.abs((2/(result.params['offset'].value +
                                             result.params[amp_string].value) + (2*result.params[amp_string].value) /
                                              (result.params['offset'].value + result.params[amp_string].value)**2) *
                                               result.params[amp_string].stderr))*100,
                                     'unit': '%'}


    result_str_dict['Phase 1'] = {'value': 180/np.pi*result.params['e1_phase'].value,
                                  'error': 180/np.pi*result.params['e1_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Phase 2'] = {'value': 180/np.pi*result.params['e2_phase'].value,
                                  'error': 180/np.pi*result.params['e2_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Phase 3'] = {'value': 180/np.pi*result.params['e3_phase'].value,
                                  'error': 180/np.pi*result.params['e3_phase'].stderr,
                                  'unit': 'deg'}

    result_str_dict['Lifetime 1'] = {'value': result.params['e1_lifetime'].value,
                                     'error': result.params['e1_lifetime'].stderr,
                                     'unit': units[0]}

    result_str_dict['Lifetime 2'] = {'value': result.params['e2_lifetime'].value,
                                     'error': result.params['e2_lifetime'].stderr,
                                     'unit': units[0]}

    result_str_dict['Lifetime 3'] = {'value': result.params['e3_lifetime'].value,
                                     'error': result.params['e3_lifetime'].stderr,
                                     'unit': units[0]}

    result_str_dict['Offset'] = {'value': result.params['offset'].value,
                                 'error': result.params['offset'].stderr,
                                 'unit': units[1]}

    result.result_str_dict = result_str_dict
    return result


def estimate_sinetriplewiththreeexpdecay(self, x_axis, data, params):
    """ Provides an estimator for initial values of three sine with offset and
        three exponential decay fitting.

    @param numpy.array x_axis: 1D axis values
    @param numpy.array data: 1D data, should have the same dimension as x_axis.
    @param lmfit.Parameters params: object includes parameter dictionary which
                                    can be set

    @return tuple (error, params):

    Explanation of the return parameter:
        int error: error code (0:OK, -1:error)
        Parameters object params: set parameters of initial values
    """

    error = self._check_1D_input(x_axis=x_axis, data=data, params=params)

    # That procedure seems to work extremely reliable: make two consecutive
    # sine offset fits where for the second the first fit is subtracted to
    # delete the first sine in the data.

    res1 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data,
        estimator=self.estimate_sineexponentialdecay)
    data_sub1 = data - res1.best_fit

    res2 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data_sub1,
        estimator=self.estimate_sineexponentialdecay)
    data_sub2 = data_sub1 - res2.best_fit

    res3 = self.make_sineexponentialdecay_fit(
        x_axis=x_axis,
        data=data_sub2,
        estimator=self.estimate_sineexponentialdecay)

    # Fill the parameter dict:
    params['e1_amplitude'].set(value=res1.params['amplitude'].value)
    params['e1_frequency'].set(value=res1.params['frequency'].value)
    params['e1_phase'].set(value=res1.params['phase'].value)
    params['e1_lifetime'].set(value=res1.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))

    params['e2_amplitude'].set(value=res2.params['amplitude'].value)
    params['e2_frequency'].set(value=res2.params['frequency'].value)
    params['e2_phase'].set(value=res2.params['phase'].value)
    params['e2_lifetime'].set(value=res2.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))

    params['e3_amplitude'].set(value=res3.params['amplitude'].value)
    params['e3_frequency'].set(value=res3.params['frequency'].value)
    params['e3_phase'].set(value=res3.params['phase'].value)
    params['e3_lifetime'].set(value=res3.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))

    params['offset'].set(value=data.mean())

    return error, params
