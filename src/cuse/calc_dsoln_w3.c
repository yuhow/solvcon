/*
 * Copyright (C) 2008-2011 Yung-Yu Chen <yyc@solvcon.net>.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#include "cuse.h"

#ifdef __CUDACC__
__global__ void cuda_calc_dsoln_w3(exedata *exd) {
    int istart = blockDim.x * blockIdx.x + threadIdx.x;
    // Two-/three-dimensional GGE definition (in c-tau scheme).
    const int ggefcs[31][3] = {
        // quadrilaterals.
        {1, 2, -1}, {2, 3, -1}, {3, 4, -1}, {4, 1, -1},
        // triangles.
        {1, 2, -1}, {2, 3, -1}, {3, 1, -1},
        // hexahedra.
        {2, 3, 5}, {6, 3, 2}, {4, 3, 6}, {5, 3, 4},
        {5, 1, 2}, {2, 1, 6}, {6, 1, 4}, {4, 1, 5},
        // tetrahedra.
        {3, 1, 2}, {2, 1, 4}, {4, 1, 3}, {2, 4, 3},
        // prisms.
        {5, 2, 4}, {3, 2, 5}, {4, 2, 3},
        {4, 1, 5}, {5, 1, 3}, {3, 1, 4},
        // pyramids
        {1, 5, 2}, {2, 5, 3}, {3, 5, 4}, {4, 5, 1},
        {1, 3, 4}, {3, 1, 2},
    };
    const int ggerng[8][2] = {
        {-1, -1}, {-2, -1}, {0, 4}, {4, 7},
        {7, 15}, {15, 19}, {19, 25}, {25, 31},
        //{0, 8}, {8, 12}, {12, 18}, {18, 24},
    };
#else
int calc_dsoln_w3(exedata *exd) {
#ifdef SOLVCON_FE
    feenableexcept(SOLVCON_FE);
#endif
#endif
    int clnfc;
    // pointers.
    int *pcltpn;
    int *pclfcs, *pfccls;
    double *pcecnd, *picecnd, *pjcecnd;
    double *pisoln, *pjsol, *pjsoln, *pdsol, *pdsoln;
    double *pjsolt;
    // scalars.
    double hdt;
    double tau, vob, voc, wgt, ofg1, sgm0;
    double grd0, grd1, grd2;
    // arrays.
    double xps[CLMFC][NDIM], dsp[CLMFC][NDIM];
    double crd[NDIM], cnd[NDIM], cndge[NDIM], sft[NDIM];
    double dst[NDIM][NDIM];
    double dnv[NDIM][NDIM];
    double udf[NEQ][NDIM];
    double gfd[MFGE][NEQ][NDIM];
    double dlt[MFGE][NEQ];
    double dla[NEQ];
    // interators.
    int icl, ifl, ifl1, ifc, jcl, ieq, ivx;
    int ig0, ig1, ig, ifg;
    hdt = exd->time_increment * 0.5;
#ifndef __CUDACC__
    #pragma omp parallel for private(clnfc, pcltpn, pclfcs, \
    pfccls, pcecnd, picecnd, pjcecnd, \
    pisoln, pjsol, pjsoln, pdsol, pdsoln, pjsolt, \
    tau, vob, voc, wgt, ofg1, sgm0, \
    grd0, grd1, grd2, \
    xps, dsp, crd, cnd, cndge, sft, dst, dnv, udf, gfd, dlt, dla, \
    icl, ifl, ifl1, ifc, jcl, \
    ieq, ivx, ig0, ig1, ig, ifg) \
    firstprivate(hdt)
    for (icl=0; icl<exd->ncell; icl++) {
#else
    icl = istart;
    if (icl < exd->ncell) {
#endif
        pcltpn = exd->cltpn + icl;  // 1 flops.
        ig0 = ggerng[pcltpn[0]][0];
        ig1 = ggerng[pcltpn[0]][1];
        ofg1 = 1.0/(ig1-ig0);
        pclfcs = exd->clfcs + icl*(CLMFC+1);

        // determine sigma0 and tau.
        sgm0 = exd->sigma0 / fabs(exd->cfl[icl]);   // 3 flops.
        tau = exd->taumin + fabs(exd->cfl[icl]) * exd->tauscale;

        // calculate the vertices of GGE with the tau parameter.
        pclfcs = exd->clfcs + icl*(CLMFC+1);
        picecnd = exd->cecnd + icl*(CLMFC+1)*NDIM;
        pcecnd = picecnd;
        clnfc = pclfcs[0];
        for (ifl=1; ifl<=clnfc; ifl++) {    // clnfc*(16+8) flops.
            ifl1 = ifl - 1;
            ifc = pclfcs[ifl];
            pfccls = exd->fccls + ifc*FCREL;
            jcl = pfccls[0] + pfccls[1] - icl;
            pjcecnd = exd->cecnd + jcl*(CLMFC+1)*NDIM;
            pcecnd += NDIM;
            // location of P/M points and displacement to neighboring solution
            // points.
            sft[0] = (picecnd[0] + pjcecnd[0])/2;
            sft[0] += exd->cnbfac*(pcecnd[0] - sft[0]);
            xps[ifl1][0] = (pjcecnd[0] - sft[0])*tau + sft[0];
            dsp[ifl1][0] = xps[ifl1][0] - pjcecnd[0];
            sft[1] = (picecnd[1] + pjcecnd[1])/2;
            sft[1] += exd->cnbfac*(pcecnd[1] - sft[1]);
            xps[ifl1][1] = (pjcecnd[1] - sft[1])*tau + sft[1];
            dsp[ifl1][1] = xps[ifl1][1] - pjcecnd[1];
#if NDIM == 3
            sft[2] = (picecnd[2] + pjcecnd[2])/2;
            sft[2] += exd->cnbfac*(pcecnd[2] - sft[2]);
            xps[ifl1][2] = (pjcecnd[2] - sft[2])*tau + sft[2];
            dsp[ifl1][2] = xps[ifl1][2] - pjcecnd[2];
#endif
        };

        // calculate average point.
        crd[0] = crd[1] = 0.0;
#if NDIM == 3
        crd[2] = 0.0;
#endif
        for (ifl=0; ifl<clnfc; ifl++) { // clnfc*(2+1) flops.
            crd[0] += xps[ifl][0];
            crd[1] += xps[ifl][1];
#if NDIM == 3
            crd[2] += xps[ifl][2];
#endif
        };
        crd[0] /= clnfc;    // 2+1 flops.
        crd[1] /= clnfc;
#if NDIM == 3
        crd[2] /= clnfc;
#endif
        // calculate GGE centroid.
        voc = cndge[0] = cndge[1] = 0.0;
#if NDIM == 3
        cndge[2] = 0.0;
#endif
        for (ig=ig0; ig<ig1; ig++) {
            cnd[0] = crd[0];
            cnd[1] = crd[1];
#if NDIM == 3
            cnd[2] = crd[2];
#endif
            for (ivx=0; ivx<NDIM; ivx++) {  // MFGE*NDIM*(4+2) flops.
                ifl = ggefcs[ig][ivx]-1;
                cnd[0] += xps[ifl][0];
                cnd[1] += xps[ifl][1];
#if NDIM == 3
                cnd[2] += xps[ifl][2];
#endif
                dst[ivx][0] = xps[ifl][0] - crd[0];
                dst[ivx][1] = xps[ifl][1] - crd[1];
#if NDIM == 3
                dst[ivx][2] = xps[ifl][2] - crd[2];
#endif
            };
            cnd[0] /= NDIM+1;   //  MFGE*(2+(4,16)) flops.
            cnd[1] /= NDIM+1;
#if NDIM == 3
            cnd[2] /= NDIM+1;
            sft[0] = dst[0][1]*dst[1][2] - dst[0][2]*dst[1][1];
            sft[1] = dst[0][2]*dst[1][0] - dst[0][0]*dst[1][2];
            sft[2] = dst[0][0]*dst[1][1] - dst[0][1]*dst[1][0];
            vob = fabs(sft[0]*dst[2][0] + sft[1]*dst[2][1] + sft[2]*dst[2][2]);
            vob /= 6;
#else
            vob = fabs(dst[0][0]*dst[1][1] - dst[0][1]*dst[1][0]);
            vob /= 2;
#endif
            voc += vob; // MFGE*(5+2) flops.
            cndge[0] += cnd[0] * vob;
            cndge[1] += cnd[1] * vob;
#if NDIM == 3
            cndge[2] += cnd[2] * vob;
#endif
        };
        cndge[0] /= voc;    // 2+1 flops.
        cndge[1] /= voc;
#if NDIM == 3
        cndge[2] /= voc;
#endif
        // calculate GGE shift.
        pcecnd = exd->cecnd + icl*(CLMFC+1)*NDIM;
        sft[0] = exd->sftfac * (pcecnd[0] - cndge[0]);  // 4+2 flops.
        sft[1] = exd->sftfac * (pcecnd[1] - cndge[1]);
#if NDIM == 3
        sft[2] = exd->sftfac * (pcecnd[2] - cndge[2]);
#endif
        for (ifl=0; ifl<clnfc; ifl++) { // clnfc*(2+1) flops.
            dsp[ifl][0] += sft[0];
            dsp[ifl][1] += sft[1];
#if NDIM == 3
            dsp[ifl][2] += sft[2];
#endif
        };

        // calculate gradient and weighting delta.
        for (ieq=0; ieq<NEQ; ieq++) {
            dla[ieq] = 0;
        };
        pisoln = exd->soln + icl*NEQ;
        for (ig=ig0; ig<ig1; ig++) {
            ifg = ig-ig0;   // MFGE*1 flops
            for (ivx=0; ivx<NDIM; ivx++) {
                ifl = ggefcs[ig][ivx];
                ifc = pclfcs[ifl];
                ifl -= 1;
                pfccls = exd->fccls + ifc*FCREL;
                jcl = pfccls[0] + pfccls[1] - icl;
                // distance.
                dst[ivx][0] = xps[ifl][0] - cndge[0]; // MFGE*NDIM*(2+1) flops.
                dst[ivx][1] = xps[ifl][1] - cndge[1];
#if NDIM == 3
                dst[ivx][2] = xps[ifl][2] - cndge[2];
#endif
                // solution difference.
                pjsol = exd->sol + jcl*NEQ;
                pjsoln = exd->soln + jcl*NEQ;
				pjsolt = exd->solt + jcl*NEQ;
                pdsol = exd->dsol + jcl*NEQ*NDIM;
                for (ieq=0; ieq<NEQ; ieq++) {   // MFGE*NDIM*NEQ*(9+2) flops.
                    voc = pjsol[ieq] + hdt*pjsolt[ieq] - pjsoln[ieq];
                    voc *= exd->taylor;
                    udf[ieq][ivx] = pjsoln[ieq] + voc - pisoln[ieq];
                    udf[ieq][ivx] += dsp[ifl][0]*pdsol[0];
                    udf[ieq][ivx] += dsp[ifl][1]*pdsol[1];
#if NDIM == 3
                    udf[ieq][ivx] += dsp[ifl][2]*pdsol[2];
#endif
                    pdsol += NDIM;
                };
            };
            // prepare inverse matrix for gradient. MFGE*(3,32) flops.
#if NDIM == 3
            dnv[0][0] = dst[1][1]*dst[2][2] - dst[1][2]*dst[2][1];
            dnv[0][1] = dst[0][2]*dst[2][1] - dst[0][1]*dst[2][2];
            dnv[0][2] = dst[0][1]*dst[1][2] - dst[0][2]*dst[1][1];
            dnv[1][0] = dst[1][2]*dst[2][0] - dst[1][0]*dst[2][2];
            dnv[1][1] = dst[0][0]*dst[2][2] - dst[0][2]*dst[2][0];
            dnv[1][2] = dst[0][2]*dst[1][0] - dst[0][0]*dst[1][2];
            dnv[2][0] = dst[1][0]*dst[2][1] - dst[1][1]*dst[2][0];
            dnv[2][1] = dst[0][1]*dst[2][0] - dst[0][0]*dst[2][1];
            dnv[2][2] = dst[0][0]*dst[1][1] - dst[0][1]*dst[1][0];
            voc = dnv[0][2]*dst[2][0] + dnv[1][2]*dst[2][1]
                + dnv[2][2]*dst[2][2];
#else
            dnv[0][0] =  dst[1][1]; dnv[0][1] = -dst[0][1];
            dnv[1][0] = -dst[1][0]; dnv[1][1] =  dst[0][0];
            voc = dst[0][0]*dst[1][1] - dst[0][1]*dst[1][0];
#endif
            // calculate grdient and weighting delta.
            for (ieq=0; ieq<NEQ; ieq++) {   // MFGE*NEQ*(17+12) flops.
                grd0 = dnv[0][0]*udf[ieq][0] + dnv[0][1]*udf[ieq][1];
#if NDIM == 3
                grd0 += dnv[0][2]*udf[ieq][2];
#endif
                grd0 /= voc;
                grd1 = dnv[1][0]*udf[ieq][0] + dnv[1][1]*udf[ieq][1];
#if NDIM == 3
                grd1 += dnv[1][2]*udf[ieq][2];
#endif
                grd1 /= voc;
#if NDIM == 3
                grd2 = dnv[2][0]*udf[ieq][0] + dnv[2][1]*udf[ieq][1];
                grd2 += dnv[2][2]*udf[ieq][2];
                grd2 /= voc;
#endif
                // store for later weight.
                gfd[ifg][ieq][0] = grd0;
                gfd[ifg][ieq][1] = grd1;
#if NDIM == 3
                gfd[ifg][ieq][2] = grd2;
#endif
                // W-1/2 weight function.
                wgt = grd0*grd0 + grd1*grd1;
#if NDIM == 3
                wgt += grd2*grd2;
#endif
                wgt = 1.0 / pow(sqrt(wgt+SOLVCON_ALMOST_ZERO), exd->alpha);
                // store and accumulate weighting function.
                dla[ieq] += wgt;
                dlt[ifg][ieq] = wgt;
            };
        };

        // calculate W-3/4 delta and sigma_max.
        // NOTE: udf is reused here.
        for (ieq=0; ieq<NEQ; ieq++) {
            udf[ieq][0] = udf[ieq][1] = 0.0;
        };
        for (ig=ig0; ig<ig1; ig++) {
            ifg = ig-ig0;
            for (ieq=0; ieq<NEQ; ieq++) {   // MFGE*NEQ*2 flops.
                wgt = dlt[ifg][ieq] / dla[ieq] - ofg1;
                dlt[ifg][ieq] = wgt;
                udf[ieq][0] = fmax(udf[ieq][0], wgt);
                udf[ieq][1] = fmin(udf[ieq][1], wgt);
            };
        };
        // NOTE: dla is reused here for sigma_max.
        for (ieq=0; ieq<NEQ; ieq++) {   // NEQ*5 flops.
            dla[ieq] = fmin(
                (1.0-ofg1)/(udf[ieq][0]+SOLVCON_ALMOST_ZERO),
                -ofg1/(udf[ieq][1]-SOLVCON_ALMOST_ZERO)
            );
            dla[ieq] = fmin(dla[ieq], sgm0);
        };

        // weight and update gradient.
        pdsoln = exd->dsoln + icl*NEQ*NDIM;
        for (ieq=0; ieq<NEQ; ieq++) {
            pdsoln[0] = pdsoln[1] = 0.0;
#if NDIM == 3
            pdsoln[2] = 0.0;
#endif
            pdsoln += NDIM;
        };
        for (ig=ig0; ig<ig1; ig++) {    // MFGE*NEQ*(6+2) flops.
            ifg = ig-ig0;
            pdsoln = exd->dsoln + icl*NEQ*NDIM;
            for (ieq=0; ieq<NEQ; ieq++) {
                wgt = ofg1 + dla[ieq]*dlt[ifg][ieq];
                pdsoln[0] += wgt*gfd[ifg][ieq][0];
                pdsoln[1] += wgt*gfd[ifg][ieq][1];
#if NDIM == 3
                pdsoln[2] += wgt*gfd[ifg][ieq][2];
#endif
                pdsoln += NDIM;
            };
        };
    };
#ifndef __CUDACC__
    return 0;
};
#else
};
extern "C" int calc_dsoln_w3(int nthread, exedata *exc, void *gexc) {
    int nblock = (exc->ncell + nthread-1) / nthread;
    cuda_calc_dsoln_w3<<<nblock, nthread>>>((exedata *)gexc);
    cudaThreadSynchronize();
    return 0;
};
#endif

// vim: set ft=cuda ts=4 et:
