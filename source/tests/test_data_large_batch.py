# SPDX-License-Identifier: LGPL-3.0-or-later
import inspect
import unittest

import numpy as np
from common import (
    gen_data,
    j_loader,
)
from packaging.version import parse as parse_version

from deepmd.common import (
    j_must_have,
)
from deepmd.descriptor import (
    DescrptSeAtten,
)
from deepmd.env import (
    tf,
)
from deepmd.fit import (
    EnerFitting,
)
from deepmd.model import (
    EnerModel,
)
from deepmd.utils.data_system import (
    DeepmdDataSystem,
)
from deepmd.utils.type_embed import (
    TypeEmbedNet,
)

GLOBAL_ENER_FLOAT_PRECISION = tf.float64
GLOBAL_TF_FLOAT_PRECISION = tf.float64
GLOBAL_NP_FLOAT_PRECISION = np.float64


@unittest.skipIf(
    parse_version(tf.__version__) < parse_version("1.15"),
    f"The current tf version {tf.__version__} is too low to run the new testing model.",
)
class TestDataLargeBatch(tf.test.TestCase):
    def setUp(self):
        gen_data(mixed_type=True)
        self.filename = __file__

    def test_data_mixed_type(self):
        jfile = "water_se_atten_mixed_type.json"
        jdata = j_loader(jfile)

        systems = j_must_have(jdata, "systems")
        batch_size = 1
        test_size = 1
        rcut = j_must_have(jdata["model"]["descriptor"], "rcut")
        type_map = j_must_have(jdata["model"], "type_map")

        data = DeepmdDataSystem(systems, batch_size, test_size, rcut, type_map=type_map)
        data_requirement = {
            "energy": {
                "ndof": 1,
                "atomic": False,
                "must": False,
                "high_prec": True,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "force": {
                "ndof": 3,
                "atomic": True,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "virial": {
                "ndof": 9,
                "atomic": False,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "atom_ener": {
                "ndof": 1,
                "atomic": True,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "atom_pref": {
                "ndof": 1,
                "atomic": True,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 3,
                "default": 0.0,
            },
        }
        data.add_dict(data_requirement)

        test_data = data.get_test()
        numb_test = 1

        jdata["model"]["descriptor"].pop("type", None)
        jdata["model"]["descriptor"]["ntypes"] = 2
        descrpt = DescrptSeAtten(**jdata["model"]["descriptor"], uniform_seed=True)
        jdata["model"]["fitting_net"]["descrpt"] = descrpt
        fitting = EnerFitting(**jdata["model"]["fitting_net"], uniform_seed=True)
        typeebd_param = jdata["model"]["type_embedding"]
        typeebd = TypeEmbedNet(
            neuron=typeebd_param["neuron"],
            resnet_dt=typeebd_param["resnet_dt"],
            activation_function=None,
            seed=typeebd_param["seed"],
            uniform_seed=True,
            padding=True,
        )
        model = EnerModel(descrpt, fitting, typeebd)

        # model._compute_dstats([test_data['coord']], [test_data['box']], [test_data['type']], [test_data['natoms_vec']], [test_data['default_mesh']])
        input_data = {
            "coord": [test_data["coord"]],
            "box": [test_data["box"]],
            "type": [test_data["type"]],
            "natoms_vec": [test_data["natoms_vec"]],
            "default_mesh": [test_data["default_mesh"]],
            "real_natoms_vec": [test_data["real_natoms_vec"]],
        }
        model._compute_input_stat(input_data, mixed_type=True)
        model.descrpt.bias_atom_e = np.array([0.0, 0.0])

        t_energy = tf.placeholder(GLOBAL_ENER_FLOAT_PRECISION, [None], name="t_energy")
        t_force = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None], name="t_force")
        t_virial = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None], name="t_virial")
        t_atom_ener = tf.placeholder(
            GLOBAL_TF_FLOAT_PRECISION, [None], name="t_atom_ener"
        )
        t_coord = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None], name="i_coord")
        t_type = tf.placeholder(tf.int32, [None], name="i_type")
        t_natoms = tf.placeholder(tf.int32, [model.ntypes + 2], name="i_natoms")
        t_box = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None, 9], name="i_box")
        t_mesh = tf.placeholder(tf.int32, [None], name="i_mesh")
        is_training = tf.placeholder(tf.bool)
        t_fparam = None
        inputs_dict = {}

        model_pred = model.build(
            t_coord,
            t_type,
            t_natoms,
            t_box,
            t_mesh,
            inputs_dict,
            suffix=self.filename + "-" + inspect.stack()[0][3],
            reuse=False,
        )

        energy = model_pred["energy"]
        force = model_pred["force"]
        virial = model_pred["virial"]
        atom_ener = model_pred["atom_ener"]

        feed_dict_test = {
            t_energy: np.reshape(test_data["energy"][:numb_test], [-1]),
            t_force: np.reshape(test_data["force"][:numb_test, :], [-1]),
            t_virial: np.reshape(test_data["virial"][:numb_test, :], [-1]),
            t_atom_ener: np.reshape(test_data["atom_ener"][:numb_test, :], [-1]),
            t_coord: np.reshape(test_data["coord"][:numb_test, :], [-1]),
            t_box: test_data["box"][:numb_test, :],
            t_type: np.reshape(test_data["type"][:numb_test, :], [-1]),
            t_natoms: test_data["natoms_vec"],
            t_mesh: test_data["default_mesh"],
            is_training: False,
        }

        sess = self.test_session().__enter__()
        sess.run(tf.global_variables_initializer())
        [e, f, v] = sess.run([energy, force, virial], feed_dict=feed_dict_test)
        # print(sess.run(model.type_embedding))
        # np.savetxt('tmp.out', sess.run(descrpt.dout, feed_dict = feed_dict_test), fmt='%.10e')
        # # print(sess.run(model.atype_embed, feed_dict = feed_dict_test))
        # print(sess.run(fitting.inputs, feed_dict = feed_dict_test))
        # print(sess.run(fitting.outs, feed_dict = feed_dict_test))
        # print(sess.run(fitting.atype_embed, feed_dict = feed_dict_test))

        e = e.reshape([-1])
        f = f.reshape([-1])
        v = v.reshape([-1])
        np.savetxt("e.out", e.reshape([1, -1]), delimiter=",")
        np.savetxt("f.out", f.reshape([1, -1]), delimiter=",")
        np.savetxt("v.out", v.reshape([1, -1]), delimiter=",")

        refe = [6.121172052273667e01]
        reff = [
            1.1546857028815118e-02,
            1.7560407103242779e-02,
            7.1301778864729290e-04,
            2.3682630974376197e-02,
            1.6842732518204180e-02,
            -2.2408109608703206e-03,
            -7.9408568690697776e-03,
            9.6856119564082792e-03,
            1.9055514693144326e-05,
            8.7017502459205160e-03,
            -2.7153030569749256e-02,
            -8.8338555421916490e-04,
            -4.3841165945453904e-02,
            5.8104108317526765e-03,
            2.6243178542006552e-03,
            7.8507845654118558e-03,
            -2.2746131839858654e-02,
            -2.3219464245160639e-04,
        ]
        refv = [
            -0.10488160947198523,
            0.016694308932682225,
            0.003444164500535988,
            0.016694308932682235,
            -0.05415326614376374,
            -0.0010792017166882334,
            0.003444164500535988,
            -0.001079201716688233,
            -0.00020932681975049773,
        ]

        refe = np.reshape(refe, [-1])
        reff = np.reshape(reff, [-1])
        refv = np.reshape(refv, [-1])

        places = 10
        np.testing.assert_almost_equal(e, refe, places)
        np.testing.assert_almost_equal(f, reff, places)
        np.testing.assert_almost_equal(v, refv, places)
        sess.close()

    def test_stripped_data_mixed_type(self):
        jfile = "water_se_atten_mixed_type.json"
        jdata = j_loader(jfile)

        systems = j_must_have(jdata, "systems")
        batch_size = 1
        test_size = 1
        rcut = j_must_have(jdata["model"]["descriptor"], "rcut")
        type_map = j_must_have(jdata["model"], "type_map")

        data = DeepmdDataSystem(systems, batch_size, test_size, rcut, type_map=type_map)
        data_requirement = {
            "energy": {
                "ndof": 1,
                "atomic": False,
                "must": False,
                "high_prec": True,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "force": {
                "ndof": 3,
                "atomic": True,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "virial": {
                "ndof": 9,
                "atomic": False,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "atom_ener": {
                "ndof": 1,
                "atomic": True,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "atom_pref": {
                "ndof": 1,
                "atomic": True,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 3,
                "default": 0.0,
            },
        }
        data.add_dict(data_requirement)

        test_data = data.get_test()
        numb_test = 1

        jdata["model"]["descriptor"].pop("type", None)
        jdata["model"]["descriptor"]["ntypes"] = 2
        jdata["model"]["descriptor"]["stripped_type_embedding"] = True
        descrpt = DescrptSeAtten(**jdata["model"]["descriptor"], uniform_seed=True)
        jdata["model"]["fitting_net"]["descrpt"] = descrpt
        fitting = EnerFitting(**jdata["model"]["fitting_net"], uniform_seed=True)
        typeebd_param = jdata["model"]["type_embedding"]
        typeebd = TypeEmbedNet(
            neuron=typeebd_param["neuron"],
            resnet_dt=typeebd_param["resnet_dt"],
            activation_function=None,
            seed=typeebd_param["seed"],
            uniform_seed=True,
            padding=True,
        )
        model = EnerModel(descrpt, fitting, typeebd)

        # model._compute_dstats([test_data['coord']], [test_data['box']], [test_data['type']], [test_data['natoms_vec']], [test_data['default_mesh']])
        input_data = {
            "coord": [test_data["coord"]],
            "box": [test_data["box"]],
            "type": [test_data["type"]],
            "natoms_vec": [test_data["natoms_vec"]],
            "default_mesh": [test_data["default_mesh"]],
            "real_natoms_vec": [test_data["real_natoms_vec"]],
        }
        model._compute_input_stat(input_data, mixed_type=True)
        model.descrpt.bias_atom_e = np.array([0.0, 0.0])

        t_energy = tf.placeholder(GLOBAL_ENER_FLOAT_PRECISION, [None], name="t_energy")
        t_force = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None], name="t_force")
        t_virial = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None], name="t_virial")
        t_atom_ener = tf.placeholder(
            GLOBAL_TF_FLOAT_PRECISION, [None], name="t_atom_ener"
        )
        t_coord = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None], name="i_coord")
        t_type = tf.placeholder(tf.int32, [None], name="i_type")
        t_natoms = tf.placeholder(tf.int32, [model.ntypes + 2], name="i_natoms")
        t_box = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None, 9], name="i_box")
        t_mesh = tf.placeholder(tf.int32, [None], name="i_mesh")
        is_training = tf.placeholder(tf.bool)
        t_fparam = None
        inputs_dict = {}

        model_pred = model.build(
            t_coord,
            t_type,
            t_natoms,
            t_box,
            t_mesh,
            inputs_dict,
            suffix=self.filename + "-" + inspect.stack()[0][3],
            reuse=False,
        )

        energy = model_pred["energy"]
        force = model_pred["force"]
        virial = model_pred["virial"]
        atom_ener = model_pred["atom_ener"]

        feed_dict_test = {
            t_energy: np.reshape(test_data["energy"][:numb_test], [-1]),
            t_force: np.reshape(test_data["force"][:numb_test, :], [-1]),
            t_virial: np.reshape(test_data["virial"][:numb_test, :], [-1]),
            t_atom_ener: np.reshape(test_data["atom_ener"][:numb_test, :], [-1]),
            t_coord: np.reshape(test_data["coord"][:numb_test, :], [-1]),
            t_box: test_data["box"][:numb_test, :],
            t_type: np.reshape(test_data["type"][:numb_test, :], [-1]),
            t_natoms: test_data["natoms_vec"],
            t_mesh: test_data["default_mesh"],
            is_training: False,
        }

        sess = self.test_session().__enter__()
        sess.run(tf.global_variables_initializer())
        [e, f, v] = sess.run([energy, force, virial], feed_dict=feed_dict_test)
        # print(sess.run(model.type_embedding))
        # np.savetxt('tmp.out', sess.run(descrpt.dout, feed_dict = feed_dict_test), fmt='%.10e')
        # # print(sess.run(model.atype_embed, feed_dict = feed_dict_test))
        # print(sess.run(fitting.inputs, feed_dict = feed_dict_test))
        # print(sess.run(fitting.outs, feed_dict = feed_dict_test))
        # print(sess.run(fitting.atype_embed, feed_dict = feed_dict_test))

        e = e.reshape([-1])
        f = f.reshape([-1])
        v = v.reshape([-1])
        np.savetxt("e11.out", e.reshape([1, -1]), delimiter=",")
        np.savetxt("f11.out", f.reshape([1, -1]), delimiter=",")
        np.savetxt("v11.out", v.reshape([1, -1]), delimiter=",")

        refe = [6.125926357944699419e01]
        reff = [
            4.071033392194846855e-03,
            1.191078506555811808e-02,
            5.710038490045591959e-04,
            2.083813511902148086e-02,
            1.050404909007916256e-02,
            -1.935131519230624082e-03,
            -1.844253334357196135e-03,
            7.073208513688628192e-03,
            -5.000418009101099666e-05,
            2.877594036828151017e-03,
            -1.849276075329028823e-02,
            -5.424378676202407318e-04,
            -3.237425532982485255e-02,
            2.747768700765259881e-03,
            2.122946741188093227e-03,
            6.431746116137571252e-03,
            -1.374305061680087571e-02,
            -1.663770232507767613e-04,
        ]
        refv = [
            -5.699812217912397783e-02,
            8.904976757403395421e-03,
            2.306167440955633578e-03,
            8.904976757403414503e-03,
            -3.502855693434053092e-02,
            -6.596869271547717252e-04,
            2.306167440955633145e-03,
            -6.596869271547715083e-04,
            -1.602012510288682446e-04,
        ]

        refe = np.reshape(refe, [-1])
        reff = np.reshape(reff, [-1])
        refv = np.reshape(refv, [-1])

        places = 10
        np.testing.assert_almost_equal(e, refe, places)
        np.testing.assert_almost_equal(f, reff, places)
        np.testing.assert_almost_equal(v, refv, places)

    def test_compressible_data_mixed_type(self):
        jfile = "water_se_atten_mixed_type.json"
        jdata = j_loader(jfile)

        systems = j_must_have(jdata, "systems")
        batch_size = 1
        test_size = 1
        rcut = j_must_have(jdata["model"]["descriptor"], "rcut")
        type_map = j_must_have(jdata["model"], "type_map")

        data = DeepmdDataSystem(systems, batch_size, test_size, rcut, type_map=type_map)
        data_requirement = {
            "energy": {
                "ndof": 1,
                "atomic": False,
                "must": False,
                "high_prec": True,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "force": {
                "ndof": 3,
                "atomic": True,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "virial": {
                "ndof": 9,
                "atomic": False,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "atom_ener": {
                "ndof": 1,
                "atomic": True,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 1,
                "default": 0.0,
            },
            "atom_pref": {
                "ndof": 1,
                "atomic": True,
                "must": False,
                "high_prec": False,
                "type_sel": None,
                "repeat": 3,
                "default": 0.0,
            },
        }
        data.add_dict(data_requirement)

        test_data = data.get_test()
        numb_test = 1

        jdata["model"]["descriptor"].pop("type", None)
        jdata["model"]["descriptor"]["ntypes"] = 2
        jdata["model"]["descriptor"]["stripped_type_embedding"] = True
        jdata["model"]["descriptor"]["attn_layer"] = 0
        descrpt = DescrptSeAtten(**jdata["model"]["descriptor"], uniform_seed=True)
        jdata["model"]["fitting_net"]["descrpt"] = descrpt
        fitting = EnerFitting(**jdata["model"]["fitting_net"], uniform_seed=True)
        typeebd_param = jdata["model"]["type_embedding"]
        typeebd = TypeEmbedNet(
            neuron=typeebd_param["neuron"],
            resnet_dt=typeebd_param["resnet_dt"],
            activation_function=None,
            seed=typeebd_param["seed"],
            uniform_seed=True,
            padding=True,
        )
        model = EnerModel(descrpt, fitting, typeebd)

        # model._compute_dstats([test_data['coord']], [test_data['box']], [test_data['type']], [test_data['natoms_vec']], [test_data['default_mesh']])
        input_data = {
            "coord": [test_data["coord"]],
            "box": [test_data["box"]],
            "type": [test_data["type"]],
            "natoms_vec": [test_data["natoms_vec"]],
            "default_mesh": [test_data["default_mesh"]],
            "real_natoms_vec": [test_data["real_natoms_vec"]],
        }
        model._compute_input_stat(input_data, mixed_type=True)
        model.descrpt.bias_atom_e = np.array([0.0, 0.0])

        t_energy = tf.placeholder(GLOBAL_ENER_FLOAT_PRECISION, [None], name="t_energy")
        t_force = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None], name="t_force")
        t_virial = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None], name="t_virial")
        t_atom_ener = tf.placeholder(
            GLOBAL_TF_FLOAT_PRECISION, [None], name="t_atom_ener"
        )
        t_coord = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None], name="i_coord")
        t_type = tf.placeholder(tf.int32, [None], name="i_type")
        t_natoms = tf.placeholder(tf.int32, [model.ntypes + 2], name="i_natoms")
        t_box = tf.placeholder(GLOBAL_TF_FLOAT_PRECISION, [None, 9], name="i_box")
        t_mesh = tf.placeholder(tf.int32, [None], name="i_mesh")
        is_training = tf.placeholder(tf.bool)
        t_fparam = None
        inputs_dict = {}

        model_pred = model.build(
            t_coord,
            t_type,
            t_natoms,
            t_box,
            t_mesh,
            inputs_dict,
            suffix=self.filename + "-" + inspect.stack()[0][3],
            reuse=False,
        )

        energy = model_pred["energy"]
        force = model_pred["force"]
        virial = model_pred["virial"]
        atom_ener = model_pred["atom_ener"]

        feed_dict_test = {
            t_energy: np.reshape(test_data["energy"][:numb_test], [-1]),
            t_force: np.reshape(test_data["force"][:numb_test, :], [-1]),
            t_virial: np.reshape(test_data["virial"][:numb_test, :], [-1]),
            t_atom_ener: np.reshape(test_data["atom_ener"][:numb_test, :], [-1]),
            t_coord: np.reshape(test_data["coord"][:numb_test, :], [-1]),
            t_box: test_data["box"][:numb_test, :],
            t_type: np.reshape(test_data["type"][:numb_test, :], [-1]),
            t_natoms: test_data["natoms_vec"],
            t_mesh: test_data["default_mesh"],
            is_training: False,
        }

        sess = self.test_session().__enter__()
        sess.run(tf.global_variables_initializer())
        [e, f, v] = sess.run([energy, force, virial], feed_dict=feed_dict_test)
        # print(sess.run(model.type_embedding))
        # np.savetxt('tmp.out', sess.run(descrpt.dout, feed_dict = feed_dict_test), fmt='%.10e')
        # # print(sess.run(model.atype_embed, feed_dict = feed_dict_test))
        # print(sess.run(fitting.inputs, feed_dict = feed_dict_test))
        # print(sess.run(fitting.outs, feed_dict = feed_dict_test))
        # print(sess.run(fitting.atype_embed, feed_dict = feed_dict_test))

        e = e.reshape([-1])
        f = f.reshape([-1])
        v = v.reshape([-1])
        np.savetxt("e.out", e.reshape([1, -1]), delimiter=",")
        np.savetxt("f.out", f.reshape([1, -1]), delimiter=",")
        np.savetxt("v.out", v.reshape([1, -1]), delimiter=",")

        refe = [4.978373241868134613e01]
        reff = [
            3.587688614359243466e00,
            3.202584939641652362e00,
            1.166711402014127957e-01,
            2.384342214774975321e00,
            3.542611694579458348e00,
            -1.916097942322055603e-01,
            -4.120123413353201869e00,
            1.474564563185293276e00,
            2.693540383300669847e-02,
            2.380464377433281431e00,
            -4.807108079981841975e00,
            -1.784915273650321821e-01,
            -5.314498717923408222e00,
            1.495140750360528958e00,
            2.602480033292806638e-01,
            1.082126924709109872e00,
            -4.907793867785092523e00,
            -3.375322576646228034e-02,
        ]
        refv = [
            -1.760844499856655432e01,
            3.767507287595555532e00,
            4.505304110104397242e-01,
            3.767507287595555088e00,
            -1.052518611764145362e01,
            -2.174256785611231313e-01,
            4.505304110104397797e-01,
            -2.174256785611231868e-01,
            -2.462288791771098315e-02,
        ]

        refe = np.reshape(refe, [-1])
        reff = np.reshape(reff, [-1])
        refv = np.reshape(refv, [-1])

        places = 10
        np.testing.assert_almost_equal(e, refe, places)
        np.testing.assert_almost_equal(f, reff, places)
        np.testing.assert_almost_equal(v, refv, places)
