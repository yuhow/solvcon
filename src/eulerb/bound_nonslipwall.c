/*
 * Copyright (C) 2010 Yung-Yu Chen <yyc@solvcon.net>.
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

#include "euler.h"

int bound_nonslipwall_soln(exedata *exd, int nbnd, int *facn) {
    // pointers.
    int *pfacn, *pfccls, *pfcnds;
    double *pndcrd, *pfccnd, *pfcnml;
    double *pisoln, *pjsoln;
    // scalars.
    double len;
    // arrays.
    double mat[NDIM][NDIM], matinv[NDIM][NDIM];
    double mom[NDIM];
    // iterators.
    int ibnd, ifc, icl, jcl;
    pfacn = facn;
    for (ibnd=0; ibnd<nbnd; ibnd++) {
        ifc = pfacn[0];
        pfccls = exd->fccls + ifc*FCREL;
        icl = pfccls[0];
        jcl = pfccls[1];
        pfcnds = exd->fcnds + ifc*(FCMND+1);
        pisoln = exd->soln + icl*NEQ;
        pjsoln = exd->soln + jcl*NEQ;
        // rotation and inverse rotation matrices.
        pfccnd = exd->fccnd + ifc*NDIM;
        pfcnml = exd->fcnml + ifc*NDIM;
        mat[0][0] = matinv[0][0] = pfcnml[0];
        mat[0][1] = matinv[1][0] = pfcnml[1];
#if NDIM == 3
        mat[0][2] = matinv[2][0] = pfcnml[2];
        pndcrd = exd->ndcrd + pfcnds[1]*NDIM;
        mat[1][0] = pndcrd[0] - pfccnd[0];
        mat[1][1] = pndcrd[1] - pfccnd[1];
        mat[1][2] = pndcrd[2] - pfccnd[2];
        len = sqrt(mat[1][0]*mat[1][0] + mat[1][1]*mat[1][1]
                 + mat[1][2]*mat[1][2]);
        mat[1][0] = matinv[0][1] = mat[1][0]/len;
        mat[1][1] = matinv[1][1] = mat[1][1]/len;
        mat[1][2] = matinv[2][1] = mat[1][2]/len;
        mat[2][0] = matinv[0][2] = mat[0][1]*mat[1][2] - mat[0][2]*mat[1][1];
        mat[2][1] = matinv[1][2] = mat[0][2]*mat[1][0] - mat[0][0]*mat[1][2];
        mat[2][2] = matinv[2][2] = mat[0][0]*mat[1][1] - mat[0][1]*mat[1][0];
#else
        mat[1][0] = matinv[0][1] =  pfcnml[1];
        mat[1][1] = matinv[1][1] = -pfcnml[0];
#endif
        // rotate momentum vector.
#if NDIM == 3
        mom[0] = mat[0][0]*pisoln[1] + mat[0][1]*pisoln[2]
               + mat[0][2]*pisoln[3];
        mom[1] = mat[1][0]*pisoln[1] + mat[1][1]*pisoln[2]
               + mat[1][2]*pisoln[3];
        mom[2] = mat[2][0]*pisoln[1] + mat[2][1]*pisoln[2]
               + mat[2][2]*pisoln[3];
#else
        mom[0] = mat[0][0]*pisoln[1] + mat[0][1]*pisoln[2];
        mom[1] = mat[1][0]*pisoln[1] + mat[1][1]*pisoln[2];
#endif
        // set momentum.
        mom[0] = -mom[0];
        mom[1] = -mom[1];
#if NDIM == 3
        mom[2] = -mom[2];
#endif
        // inversely rotate momentum vector.
#if NDIM == 3
        pjsoln[1] = matinv[0][0]*mom[0] + matinv[0][1]*mom[1]
                  + matinv[0][2]*mom[2];
        pjsoln[2] = matinv[1][0]*mom[0] + matinv[1][1]*mom[1]
                  + matinv[1][2]*mom[2];
        pjsoln[3] = matinv[2][0]*mom[0] + matinv[2][1]*mom[1]
                  + matinv[2][2]*mom[2];
#else
        pjsoln[1] = matinv[0][0]*mom[0] + matinv[0][1]*mom[1];
        pjsoln[2] = matinv[1][0]*mom[0] + matinv[1][1]*mom[1];
#endif
        // set solutions.
        pjsoln[0] = pisoln[0];
        pjsoln[1+NDIM] = pisoln[1+NDIM];
        // advance boundary face.
        pfacn += BFREL;
    };
    return 0;
}
int bound_nonslipwall_dsoln(exedata *exd, int nbnd, int *facn) {
    // pointers.
    int *pfacn, *pfccls, *pfcnds;
    double *pidsoln, *pjdsoln, *pdsoln;
    double *pndcrd, *pfccnd, *pfcnml;
    // scalars.
    double len;
    // arrays.
    double vec[NEQ][NDIM];
    double mat[NDIM][NDIM], matinv[NDIM][NDIM];
    // iterators.
    int ibnd, ifc, icl, jcl, ieq;
    pfacn = facn;
    for (ibnd=0; ibnd<nbnd; ibnd++) {
        ifc = pfacn[0];
        pfccls = exd->fccls + ifc*FCREL;
        icl = pfccls[0];
        jcl = pfccls[1];
        pfcnds = exd->fcnds + ifc*(FCMND+1);
        pidsoln = exd->dsoln + icl*NEQ*NDIM;
        pjdsoln = exd->dsoln + jcl*NEQ*NDIM;
        // coordinate transformation and set transformed vectors.
        pfccnd = exd->fccnd + ifc*NDIM;
        pfcnml = exd->fcnml + ifc*NDIM;
        mat[0][0] = matinv[0][0] = pfcnml[0];
        mat[0][1] = matinv[1][0] = pfcnml[1];
#if NDIM == 3
        mat[0][2] = matinv[2][0] = pfcnml[2];
        pndcrd = exd->ndcrd + pfcnds[1]*NDIM;
        mat[1][0] = pndcrd[0] - pfccnd[0];
        mat[1][1] = pndcrd[1] - pfccnd[1];
        mat[1][2] = pndcrd[2] - pfccnd[2];
        len = sqrt(mat[1][0]*mat[1][0] + mat[1][1]*mat[1][1]
                 + mat[1][2]*mat[1][2]);
        mat[1][0] = matinv[0][1] = mat[1][0]/len;
        mat[1][1] = matinv[1][1] = mat[1][1]/len;
        mat[1][2] = matinv[2][1] = mat[1][2]/len;
        mat[2][0] = matinv[0][2] = mat[0][1]*mat[1][2] - mat[0][2]*mat[1][1];
        mat[2][1] = matinv[1][2] = mat[0][2]*mat[1][0] - mat[0][0]*mat[1][2];
        mat[2][2] = matinv[2][2] = mat[0][0]*mat[1][1] - mat[0][1]*mat[1][0];
#else
        mat[1][0] = matinv[0][1] =  pfcnml[1];
        mat[1][1] = matinv[1][1] = -pfcnml[0];
#endif
        pdsoln = pidsoln;
        for (ieq=0; ieq<NEQ; ieq++) {
#if NDIM == 3
            vec[ieq][0] = mat[0][0]*pdsoln[0] + mat[0][1]*pdsoln[1]
                        + mat[0][2]*pdsoln[2];
            vec[ieq][1] = mat[1][0]*pdsoln[0] + mat[1][1]*pdsoln[1]
                        + mat[1][2]*pdsoln[2];
            vec[ieq][2] = mat[2][0]*pdsoln[0] + mat[2][1]*pdsoln[1]
                        + mat[2][2]*pdsoln[2];
#else
            vec[ieq][0] = mat[0][0]*pdsoln[0] + mat[0][1]*pdsoln[1];
            vec[ieq][1] = mat[1][0]*pdsoln[0] + mat[1][1]*pdsoln[1];
#endif
            pdsoln += NDIM;
        };
        // set wall condition in the rotated coordinate;
        vec[0][0] = -vec[0][0];
        /// x-momentum.
        vec[1][1] = -vec[1][1];
#if NDIM == 3
        vec[1][2] = -vec[1][2];
#endif
        /// y-momentum.
        vec[2][1] = -vec[2][1];
#if NDIM == 3
        vec[2][2] = -vec[2][2];
#endif
#if NDIM == 3
        /// z-momentum.
        vec[3][1] = -vec[3][1];
        vec[3][2] = -vec[3][2];
#endif
        vec[1+NDIM][0] = -vec[1+NDIM][0];
        // inversely transform the coordinate and set ghost gradient.
        pdsoln = pjdsoln;
        for (ieq=0; ieq<NEQ; ieq++) {
#if NDIM == 3
            pdsoln[0] = matinv[0][0]*vec[ieq][0] + matinv[0][1]*vec[ieq][1]
                      + matinv[0][2]*vec[ieq][2];
            pdsoln[1] = matinv[1][0]*vec[ieq][0] + matinv[1][1]*vec[ieq][1]
                      + matinv[1][2]*vec[ieq][2];
            pdsoln[2] = matinv[2][0]*vec[ieq][0] + matinv[2][1]*vec[ieq][1]
                      + matinv[2][2]*vec[ieq][2];
#else
            pdsoln[0] = matinv[0][0]*vec[ieq][0] + matinv[0][1]*vec[ieq][1];
            pdsoln[1] = matinv[1][0]*vec[ieq][0] + matinv[1][1]*vec[ieq][1];
#endif
            pdsoln += NDIM;
        };
        // advance boundary face.
        pfacn += BFREL;
    };
    return 0;
}
// vim: set ts=4 et:
