# Copyright 2016 The Johns Hopkins University Applied Physics Laboratory
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from rest_framework import renderers
import blosc
import numpy as np
import zlib
import io


class BloscPythonRenderer(renderers.BaseRenderer):
    """ A DRF renderer for a blosc encoded cube of data using the numpy interface

    Should only be used by applications written in python
    """
    media_type = 'application/blosc-python'
    format = 'bin'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):

        if not data["data"].data.flags['C_CONTIGUOUS']:
            data["data"].data = np.ascontiguousarray(data["data"].data, dtype=data["data"].data.dtype)

        # Return data, squeezing time dimension if only a single point
        if data["time_request"]:
            return blosc.pack_array(data["data"].data)
        else:
            return blosc.pack_array(np.squeeze(data["data"].data, axis=(0,)))


class BloscRenderer(renderers.BaseRenderer):
    """ A DRF renderer for a blosc encoded cube of data

    """
    media_type = 'application/blosc'
    format = 'bin'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):

        if not data["data"].data.flags['C_CONTIGUOUS']:
            data["data"].data = np.ascontiguousarray(data["data"].data, dtype=data["data"].data.dtype)

        # Return data, squeezing time dimension if only a single point
        if data["time_request"]:
            return blosc.compress(data["data"].data, typesize=renderer_context['view'].bit_depth)
        else:
            return blosc.compress(np.squeeze(data["data"].data, axis=(0,)),
                                  typesize=renderer_context['view'].bit_depth)


class NpygzRenderer(renderers.BaseRenderer):
    """ A DRF renderer for a gzip compressed npy encoded cube of data, following a similar method as ndstore for
    compatibility with existing tools

    """
    media_type = 'application/npygz'
    format = 'bin'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):

        if not data["data"].data.flags['C_CONTIGUOUS']:
            data["data"].data = np.ascontiguousarray(data["data"].data, dtype=data["data"].data.dtype)

        # Return data, squeezing time dimension if only a single point
        if not data["time_request"]:
            data["data"].data = np.squeeze(data["data"].data, axis=(0,))

        # Save Data to npy
        npy_file = io.BytesIO()
        np.save(npy_file, data["data"].data, allow_pickle=False)

        # Compress npy
        npy_gz = zlib.compress(npy_file.getvalue())

        # Send file
        npy_gz_file = io.BytesIO(npy_gz)
        npy_gz_file.seek(0)
        return npy_gz_file.read()


class JpegRenderer(renderers.BaseRenderer):
    """ A DRF renderer for a jpeg 'sprite sheet' encoded cube of data. Here, we concat z-slices

    """
    media_type = 'image/jpeg'
    format = 'jpg'
    charset = None

    def render(self, data, media_type=None, renderer_context=None):

        # Return data, squeezing time dimension as this only works with 3D data
        if not data["time_request"]:
            self.render_style = 'binary'
            data["data"].data = np.squeeze(data["data"].data, axis=(0,))
        else:
            # This appears to contain time data. Error out
            self.media_type = 'application/json'
            self.format = 'json'
            err_msg = {"status": 400, "message": "The cutout service JPEG interface does not support 4D cutouts",
                       "code": 2003}
            return err_msg

        if renderer_context['view'].bit_depth != 8:
            # This appears to contain time data. Error out
            self.media_type = 'application/json'
            self.format = 'json'
            err_msg = {"status": 400, "message": "The cutout service JPEG interface does not support 4D cutouts",
                       "code": 2003}
            return err_msg

        # Reshape matrix

        # Save to Image
        img_file = io.BytesIO()
        np.save(npy_file, data["data"].data, allow_pickle=False)

        # Compress npy
        npy_gz = zlib.compress(npy_file.getvalue())

        # Send file
        npy_gz_file = io.BytesIO(npy_gz)
        npy_gz_file.seek(0)
        return npy_gz_file.read()
