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

from django.conf import settings
import blosc

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework.test import force_authenticate
from rest_framework import status

from bosstiles.views import Tiles
from bossspatialdb.views import Cutout

from bosscore.test.setup_db import SetupTestDB
from bosscore.error import BossError

import numpy as np

from unittest.mock import patch
from mockredis import mock_strict_redis_client

import spdb
import bossutils

version = settings.BOSS_VERSION

_test_globals = {'kvio_engine': None}


class MockBossConfig(bossutils.configuration.BossConfig):
    """Basic mock for BossConfig so 'test databases' are used for redis (1) instead of the default where real data
    can live (0)"""
    def __init__(self):
        super().__init__()
        self.config["aws"]["cache-db"] = "1"
        self.config["aws"]["cache-state-db"] = "1"

    def read(self, filename):
        pass

    def __getitem__(self, key):
        return self.config[key]


class MockSpatialDB(spdb.spatialdb.SpatialDB):
    """mock for redis kvio so the actual server isn't used during unit testing, but a static mockredis-py instead"""

    @patch('bossutils.configuration.BossConfig', MockBossConfig)
    @patch('redis.StrictRedis', mock_strict_redis_client)
    def __init__(self):
        super().__init__()

        if not _test_globals['kvio_engine']:
            _test_globals['kvio_engine'] = spdb.spatialdb.KVIO.get_kv_engine('redis')

        self.kvio = _test_globals['kvio_engine']


class TileInterfaceViewUint8TestMixin(object):

    def test_channel_uint8_cuboid_aligned_no_offset_no_time_blosc(self):
        """ Test uint8 data, cuboid aligned, no offset, no time samples"""

        test_mat = np.random.randint(1, 254, (16, 128, 128))
        test_mat = test_mat.astype(np.uint8)
        h = test_mat.tobytes()
        bb = blosc.compress(h, typesize=8)

        # Create request
        factory = APIRequestFactory()
        request = factory.post('/' + version + '/cutout/col1/exp1/channel1/0/0:128/0:128/0:16/', bb,
                               content_type='application/blosc')
        # log in user
        force_authenticate(request, user=self.user)

        # Make request
        response = Cutout.as_view()(request, collection='col1', experiment='exp1', dataset='channel1',
                                    resolution='0', x_range='0:128', y_range='0:128', z_range='0:16')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create Request to get data you posted
        request = factory.get('/' + version + '/tiles/col1/exp1/channel1/xy/0/0:128/0:128/1/',
                              accepts='image/png')

        # log in user
        force_authenticate(request, user=self.user)

        # Make request
        response = Tiles.as_view()(request, collection='col1', experiment='exp1', dataset='channel1',
                                    orientation='xy', resolution='0', x_args='0:128', y_args='0:128', z_args='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # # Decompress
        # raw_data = blosc.decompress(response.content)
        # data_mat = np.fromstring(raw_data, dtype=np.uint8)
        # data_mat = np.reshape(data_mat, (16, 128, 128), order='C')
        #
        # # Test for data equality (what you put in is what you got back!)
        # np.testing.assert_array_equal(data_mat, test_mat)




@patch('redis.StrictRedis', mock_strict_redis_client)
@patch('bossutils.configuration.BossConfig', MockBossConfig)
@patch('spdb.spatialdb.kvio.KVIO', MockSpatialDB)
class TestTileInterfaceView(TileInterfaceViewUint8TestMixin, APITestCase):

    def setUp(self):
        """
        Initialize the database
        :return:
        """
        # Create a user
        dbsetup = SetupTestDB()
        self.user = dbsetup.create_user('testuser')

        # Populate DB
        dbsetup.insert_spatialdb_test_data()

        # Mock config parser so dummy params get loaded (redis is also mocked)
        self.patcher = patch('bossutils.configuration.BossConfig', MockBossConfig)
        self.mock_tests = self.patcher.start()

        self.spdb_patcher = patch('spdb.spatialdb.SpatialDB', MockSpatialDB)
        self.mock_spdb = self.spdb_patcher.start()

    def tearDown(self):
        # Stop mocking
        self.mock_tests = self.patcher.stop()
        self.mock_spdb = self.spdb_patcher.stop()