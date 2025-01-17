// SPDX-License-Identifier: LGPL-3.0-or-later
#include <gtest/gtest.h>

#include <iostream>

#include "device.h"
#include "env_mat.h"
#include "fmt_nlist.h"
#include "neighbor_list.h"
#include "prod_virial_grad.h"

class TestProdVirialGradA : public ::testing::Test {
 protected:
  std::vector<double> posi = {12.83, 2.56, 2.18, 12.09, 2.87, 2.74,
                              00.25, 3.32, 1.68, 3.36,  3.00, 1.81,
                              3.51,  2.51, 2.60, 4.27,  3.22, 1.56};
  std::vector<int> atype = {0, 1, 1, 0, 1, 1};
  std::vector<double> posi_cpy;
  std::vector<int> atype_cpy;
  int ntypes = 2;
  int nloc, nall, nnei, ndescrpt;
  double rc = 6;
  double rc_smth = 0.8;
  SimulationRegion<double> region;
  std::vector<int> mapping, ncell, ngcell;
  std::vector<int> sec_a = {0, 5, 10};
  std::vector<int> sec_r = {0, 0, 0};
  std::vector<int> nat_stt, ext_stt, ext_end;
  std::vector<std::vector<int>> nlist_a_cpy, nlist_r_cpy;
  std::vector<double> grad;
  std::vector<double> env, env_deriv, rij;
  std::vector<int> nlist;
  std::vector<int> fmt_nlist_a;
  std::vector<double> expected_grad_net = {
      5.01828,  4.97546,  -0.09569, -1.15305, 0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  -0.61704,
      1.06623,  0.15319,  0.24608,  5.28467,  -2.59553, 3.00729,  -8.19962,
      5.03021,  5.02151,  -0.86956, 0.26289,  2.75500,  2.70125,  0.22900,
      -0.54729, 0.00000,  0.00000,  0.00000,  0.00000,  -0.61704, -1.06623,
      -0.15319, -0.24608, 2.32844,  2.23467,  -0.16758, -0.70940, 0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  1.74748,  -0.30379, -1.11004,
      -3.49833, 2.42774,  2.39284,  -0.45567, -0.22216, 0.60993,  0.59054,
      0.02135,  -0.15332, 0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  5.28467,  2.59553,  -3.00729, 8.19962,
      4.77234,  4.62396,  -1.90919, -0.44792, 0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  1.74748,  0.30379,  1.11004,  3.49833,  4.06655,
      3.57849,  -2.07817, 0.88468,  3.61241,  3.58881,  -0.57839, -0.39969,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  5.01828,  -4.97546, 0.09569,  1.15305,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.07573,  -3.82089, -2.40143, -0.67375, 9.64382,  8.39638,  -2.48922,
      -9.00792, 4.77234,  -4.62396, 1.90919,  0.44792,  2.32844,  -2.23467,
      0.16758,  0.70940,  0.00000,  0.00000,  0.00000,  0.00000,  0.07573,
      3.82089,  2.40143,  0.67375,  5.03021,  -5.02151, 0.86956,  -0.26289,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  1.44012,  -1.15994,
      -0.66718, -3.33981, 4.06655,  -3.57849, 2.07817,  -0.88468, 2.42774,
      -2.39284, 0.45567,  0.22216,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  9.64382,  -8.39638, 2.48922,
      9.00792,  2.75500,  -2.70125, -0.22900, 0.54729,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,  0.00000,  1.44012,  1.15994,  0.66718,  3.33981,
      3.61241,  -3.58881, 0.57839,  0.39969,  0.60993,  -0.59054, -0.02135,
      0.15332,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,  0.00000,
      0.00000,  0.00000,
  };

  void SetUp() override {
    double box[] = {13., 0., 0., 0., 13., 0., 0., 0., 13.};
    region.reinitBox(box);
    copy_coord(posi_cpy, atype_cpy, mapping, ncell, ngcell, posi, atype, rc,
               region);
    nloc = posi.size() / 3;
    nall = posi_cpy.size() / 3;
    nnei = sec_a.back();
    ndescrpt = nnei * 4;
    nat_stt.resize(3);
    ext_stt.resize(3);
    ext_end.resize(3);
    for (int dd = 0; dd < 3; ++dd) {
      ext_stt[dd] = -ngcell[dd];
      ext_end[dd] = ncell[dd] + ngcell[dd];
    }
    build_nlist(nlist_a_cpy, nlist_r_cpy, posi_cpy, nloc, rc, rc, nat_stt,
                ncell, ext_stt, ext_end, region, ncell);
    nlist.resize(nloc * nnei);
    env.resize(nloc * ndescrpt);
    env_deriv.resize(nloc * ndescrpt * 3);
    rij.resize(nloc * nnei * 3);
    for (int ii = 0; ii < nloc; ++ii) {
      // format nlist and record
      format_nlist_i_cpu<double>(fmt_nlist_a, posi_cpy, atype_cpy, ii,
                                 nlist_a_cpy[ii], rc, sec_a);
      for (int jj = 0; jj < nnei; ++jj) {
        nlist[ii * nnei + jj] = fmt_nlist_a[jj];
      }
      std::vector<double> t_env, t_env_deriv, t_rij;
      // compute env_mat and its deriv, record
      deepmd::env_mat_a_cpu<double>(t_env, t_env_deriv, t_rij, posi_cpy,
                                    atype_cpy, ii, fmt_nlist_a, sec_a, rc_smth,
                                    rc);
      for (int jj = 0; jj < ndescrpt; ++jj) {
        env[ii * ndescrpt + jj] = t_env[jj];
        for (int dd = 0; dd < 3; ++dd) {
          env_deriv[ii * ndescrpt * 3 + jj * 3 + dd] = t_env_deriv[jj * 3 + dd];
        }
      }
      for (int jj = 0; jj < nnei * 3; ++jj) {
        rij[ii * nnei * 3 + jj] = t_rij[jj];
      }
    }
    grad.resize(9);
    for (int ii = 0; ii < 9; ++ii) {
      grad[ii] = 10 - ii * 1.;
    }
  }
  void TearDown() override {}
};

TEST_F(TestProdVirialGradA, cpu) {
  std::vector<double> grad_net(nloc * ndescrpt);
  int n_a_sel = nnei;
  deepmd::prod_virial_grad_a_cpu<double>(&grad_net[0], &grad[0], &env_deriv[0],
                                         &rij[0], &nlist[0], nloc, nnei);
  EXPECT_EQ(grad_net.size(), nloc * ndescrpt);
  EXPECT_EQ(grad_net.size(), expected_grad_net.size());
  for (int jj = 0; jj < grad_net.size(); ++jj) {
    EXPECT_LT(fabs(grad_net[jj] - expected_grad_net[jj]), 1e-5);
  }
  // for (int jj = 0; jj < nloc * ndescrpt; ++jj){
  //   printf("%8.5f, ", grad_net[jj]);
  // }
  // printf("\n");
}

#if GOOGLE_CUDA
TEST_F(TestProdVirialGradA, gpu) {
  std::vector<double> grad_net(nloc * ndescrpt);
  int n_a_sel = nnei;
  int* nlist_dev = NULL;
  double *grad_net_dev = NULL, *grad_dev = NULL, *env_deriv_dev = NULL,
         *rij_dev = NULL;

  deepmd::malloc_device_memory_sync(nlist_dev, nlist);
  deepmd::malloc_device_memory_sync(grad_dev, grad);
  deepmd::malloc_device_memory_sync(env_deriv_dev, env_deriv);
  deepmd::malloc_device_memory_sync(rij_dev, rij);
  deepmd::malloc_device_memory(grad_net_dev, nloc * ndescrpt);
  deepmd::prod_virial_grad_a_gpu_cuda<double>(
      grad_net_dev, grad_dev, env_deriv_dev, rij_dev, nlist_dev, nloc, nnei);
  deepmd::memcpy_device_to_host(grad_net_dev, grad_net);
  deepmd::delete_device_memory(nlist_dev);
  deepmd::delete_device_memory(grad_dev);
  deepmd::delete_device_memory(env_deriv_dev);
  deepmd::delete_device_memory(rij_dev);
  deepmd::delete_device_memory(grad_net_dev);

  EXPECT_EQ(grad_net.size(), nloc * ndescrpt);
  EXPECT_EQ(grad_net.size(), expected_grad_net.size());
  for (int jj = 0; jj < grad_net.size(); ++jj) {
    EXPECT_LT(fabs(grad_net[jj] - expected_grad_net[jj]), 1e-5);
  }
  // for (int jj = 0; jj < nloc * ndescrpt; ++jj){
  //   printf("%8.5f, ", grad_net[jj]);
  // }
  // printf("\n");
}
#endif  // GOOGLE_CUDA

#if TENSORFLOW_USE_ROCM
TEST_F(TestProdVirialGradA, gpu) {
  std::vector<double> grad_net(nloc * ndescrpt);
  int n_a_sel = nnei;
  int* nlist_dev = NULL;
  double *grad_net_dev = NULL, *grad_dev = NULL, *env_deriv_dev = NULL,
         *rij_dev = NULL;

  deepmd::malloc_device_memory_sync(nlist_dev, nlist);
  deepmd::malloc_device_memory_sync(grad_dev, grad);
  deepmd::malloc_device_memory_sync(env_deriv_dev, env_deriv);
  deepmd::malloc_device_memory_sync(rij_dev, rij);
  deepmd::malloc_device_memory(grad_net_dev, nloc * ndescrpt);
  deepmd::prod_virial_grad_a_gpu_rocm<double>(
      grad_net_dev, grad_dev, env_deriv_dev, rij_dev, nlist_dev, nloc, nnei);
  deepmd::memcpy_device_to_host(grad_net_dev, grad_net);
  deepmd::delete_device_memory(nlist_dev);
  deepmd::delete_device_memory(grad_dev);
  deepmd::delete_device_memory(env_deriv_dev);
  deepmd::delete_device_memory(rij_dev);
  deepmd::delete_device_memory(grad_net_dev);

  EXPECT_EQ(grad_net.size(), nloc * ndescrpt);
  EXPECT_EQ(grad_net.size(), expected_grad_net.size());
  for (int jj = 0; jj < grad_net.size(); ++jj) {
    EXPECT_LT(fabs(grad_net[jj] - expected_grad_net[jj]), 1e-5);
  }
  // for (int jj = 0; jj < nloc * ndescrpt; ++jj){
  //   printf("%8.5f, ", grad_net[jj]);
  // }
  // printf("\n");
}
#endif  // TENSORFLOW_USE_ROCM
