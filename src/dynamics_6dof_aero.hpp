// ******************************************************
// Project Name    : ForRocket
// File Name       : dynamics_6dof_aero.hpp
// Creation Date   : 2019/10/20
//
// Copyright © 2019 Susumu Tanaka. All rights reserved.
// ******************************************************

#ifndef DYNAMICS6DOFAERO_HPP_
#define DYNAMICS6DOFAERO_HPP_

#include "dynamics_base.hpp"
#include "rocket.hpp"

namespace forrocket {
    class Dynamics6dofAero : public DynamicsBase {
        public:
            Dynamics6dofAero() {};
            Dynamics6dofAero(Rocket* rocket);

            void operator()(const state& x, state& dx, const double t);

        private:
            Rocket* p_rocket;
    };
}

#endif
