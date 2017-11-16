import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate
from scipy.integrate import odeint

import Simulator.coordinate as coord
import Simulator.environment as env

def dynamics(x, t, rocket, simulator):
    Pos_ENU = x[0:3]
    altitude = Pos_ENU[2]
    Vel_ENU = x[3:6]
    Vel_Body = x[6:9]
    omega_Body = x[9:12]
    quat = x[12:16]
    mf = x[16]
    mox = x[17]
    quat = coord.quat_normalize(quat)

    # Translation coordinate
    DCM_ENU2Body = coord.DCM_ENU2Body_quat(quat)
    DCM_Body2ENU = DCM_ENU2Body.transpose()

    # Attitude
    # azimuth, elevation, roll = coord.quat2euler(DCM_ENU2Body)

    # alpha beta Vel_Air
    wind_ENU = env.Wind_ENU(simulator.vel_wind, simulator.angle_wind, altitude, rocket.Wind_refAltitude, rocket.Wind_power_exp)
    Vel_air = DCM_ENU2Body.dot(Vel_ENU - wind_ENU)
    Vel_air_abs = np.linalg.norm(Vel_air)
    u = Vel_air[0]
    v = Vel_air[1]
    w = Vel_air[2]
    # if Vel_air_abs < 0.0 or np.abs(u) < 0.0:
    #     alpha = 0.0
    #     beta = 0.0
    # else:
    #     alpha = np.arctan2(w, u)
    #     beta = np.arcsin(-v / Vel_air_abs)
    alpha = np.arctan2(w, u)
    beta = np.arcsin(-v / Vel_air_abs)

    # Air Condition
    g0 = 9.80665
    g = np.array([0.0, 0.0, -env.gravity(altitude)])
    Ta0, Pa0, rho0, Cs0 = env.std_atmo(0.0)
    Ta, Pa, rho, Cs = env.std_atmo(altitude)
    Mach = Vel_air_abs / Cs
    dynamic_pressure = 0.5 * rho * Vel_air_abs ** 2

    # Mass
    if rocket.thrust(t) <= 0.0:
        thrust = np.zeros(3)
        Isp = 0.0
        mdot_p = 0.0
        mdot_f = 0.0
        mdot_ox = 0.0
    else:
        mdot_p = rocket.thrust(t) / (rocket.Isp * g0)
        mdot_f = rocket.mdot_f
        mdot_ox = mdot_p - mdot_f
        pressure_thrust = (Pa0 - Pa) * rocket.Ae
        thrust = np.array([rocket.thrust(t) + pressure_thrust, 0.0, 0.0])
        Isp = rocket.Isp + pressure_thrust / (mdot_p * g0)
        # Limit Increase and Empty Oxidizers
        if mdot_ox < 0.0:
            mdot_ox = 0.0
    # Limit Negative Propellant Mass
    if mf <= rocket.mf_after:
        mdot_f = 0.0
        mf = rocket.mf_after
    if mox <= 0.0:
        mdot_ox = 0.0
        mox = 0.0
    mp = mf + mox
    m = rocket.ms + mp

    # Aero Force
    drag = dynamic_pressure * rocket.Cd(Mach) * rocket.A
    normal = dynamic_pressure * rocket.CNa(Mach) * rocket.A
    F_aero = np.array([-drag, normal * beta, -normal * alpha])

    # Newton Equation
    Force = (thrust + F_aero)
    Acc_Body =  Force / m + DCM_ENU2Body.dot(g)
    Acc_ENU = DCM_Body2ENU.dot(Force) / m + g

    # Center of Gravity
    Lcg_ox_fromend = rocket.L_motor + (mox / rocket.m0_ox) * (rocket.Lcg0_ox - rocket.L_motor)
    Lcg_ox = rocket.L - Lcg_ox_fromend
    Lcg_p = (mf * rocket.Lcg_f + mox * Lcg_ox) / mp
    Lcg = (mp * Lcg_p + rocket.ms * rocket.Lcg_s) / m
    Lcp = rocket.Lcp(Mach)

    # Fuel Inertia Moment
    Ij_f_pitch = mf * ((rocket.d_port_f ** 2 + rocket.d_out_f ** 2) / 4.0 + rocket.L_f / 3.0) / 4.0
    Ij_f_roll = mf * (rocket.d_port_f ** 2 + rocket.d_out_f ** 2) / 8.0

    # Offset Inertia Moment
    Ij_s_pitch = rocket.Ij0_s_pitch + rocket.ms * (Lcg - rocket.Lcg_s) ** 2
    Ij_f_pitch += mf * (Lcg - rocket.Lcg_f) ** 2
    Ij_pitch = Ij_s_pitch + Ij_f_pitch
    Ij_roll = rocket.Ij0_s_roll + Ij_f_roll
    Ij = np.array([Ij_roll, Ij_pitch, Ij_pitch])
    Ijdot_f = np.array([Ij_f_roll * mdot_f / mf, Ij_f_pitch * mdot_f / mf, Ij_f_pitch * mdot_f / mf])

    # Aero Moment
    moment_aero = np.array([0.0, F_aero[2] * (Lcp - Lcg), -F_aero[1] * (Lcp - Lcg)])

    # Aero Dumping Moment
    moment_aero_dumping = np.zeros(3)
    moment_aero_dumping[0] = dynamic_pressure * rocket.Clp * rocket.A * rocket.d ** 2 * 0.5 / Vel_air_abs * omega_Body[0]
    moment_aero_dumping[1] = dynamic_pressure * rocket.Cmq * rocket.A * rocket.L ** 2 * 0.5 / Vel_air_abs * omega_Body[1]
    moment_aero_dumping[2] = dynamic_pressure * rocket.Cnr * rocket.A * rocket.L ** 2 * 0.5 / Vel_air_abs * omega_Body[2]

    # Jet Dumping Moment
    moment_jet_dumping = np.zeros(3)
    # moment_jet_dumping[0] = (-Ijdot_f[0] + mdot_p * 0.5 * (0.25 * rocket.de ** 2)) * omega_Body[0]
    # moment_jet_dumping[1] = (-Ijdot_f[1] + mdot_p * ((Lcg - Lcg_p) ** 2 - (rocket.L - Lcg_p) ** 2)) * omega_Body[1]
    # moment_jet_dumping[2] = (-Ijdot_f[2] + mdot_p * ((Lcg - Lcg_p) ** 2 - (rocket.L - Lcg_p) ** 2)) * omega_Body[2]
    # moment_jet_dumping[0] = -(mdot_p * 0.5 * (0.25 * rocket.de ** 2)) * omega_Body[0]
    moment_jet_dumping[0] = 0.0
    moment_jet_dumping[1] = -(mdot_p * ((Lcg - Lcg_p) ** 2 - (rocket.L - Lcg_p) ** 2)) * omega_Body[1]
    moment_jet_dumping[2] = -(mdot_p * ((Lcg - Lcg_p) ** 2 - (rocket.L - Lcg_p) ** 2)) * omega_Body[2]

    # Euler Equation
    moment = moment_aero + moment_aero_dumping + moment_jet_dumping
    p = omega_Body[0]
    q = omega_Body[1]
    r = omega_Body[2]
    omegadot = np.zeros(3)
    omegadot[0] = ((Ij[1] - Ij[2]) * q * r + moment[0]) / Ij[0]
    omegadot[1] = ((Ij[2] - Ij[0]) * p * r + moment[1]) / Ij[1]
    omegadot[2] = ((Ij[0] - Ij[1]) * p * q + moment[2]) / Ij[2]

    # Kinematic Equation
    tersor_0 = [0.0, r, -q, p]
    tersor_1 = [-r, 0.0, p, q]
    tersor_2 = [q, -p, 0.0, r]
    tersor_3 = [-p, -q, -r, 0.0]
    tersor = np.array([tersor_0, tersor_1, tersor_2, tersor_3])
    quatdot = 0.5 * tersor.dot(quat)

    if altitude / np.sin(np.deg2rad(np.abs(rocket.elevation0))) < rocket.launcher_rail and t < 0.5:
        omegadot = np.array([0.0] * 3)
        quatdot = np.array([0.0] * 4)
        simulator.vel_launch_clear = Vel_Body[0]
        simulator.acc_launch_clear = Acc_Body[0]

    dx = np.zeros(18)
    dx[0:3] = Vel_ENU  # Pos_ENU
    dx[3:6] = Acc_ENU  # Vel_ENU
    dx[6:9] = Acc_Body  # Vel_Body
    dx[9:12] = omegadot  # omega_Body
    dx[12:16] = quatdot  # quat
    dx[16] = -mdot_f  # mf
    dx[17] = -mdot_ox  # mox

    return dx

def parachute_dynamics(x, t, rocket, simulator):
    m = simulator.m_apogee
    Pos_ENU = x[0:3]
    altitude = Pos_ENU[2]
    Vel_descent = x[3]

    wind_ENU = env.Wind_ENU(simulator.vel_wind, simulator.angle_wind, altitude, rocket.Wind_refAltitude, rocket.Wind_power_exp)
    Vel_ENU = np.array([wind_ENU[0], wind_ENU[1], Vel_descent])

    g = np.array([0.0, 0.0, -env.gravity(altitude)])
    Ta, Pa, rho, Cs = env.std_atmo(altitude)
    CdS = rocket.CdS1 + rocket.CdS2 if altitude <= rocket.alt_sepa2 else rocket.CdS1
    drag = 0.5 * rho * CdS * Vel_ENU[2] ** 2
    Acc = drag / m + g[2]
    dx = np.zeros(4)
    dx[0:3] = Vel_ENU  # Pos_ENU
    dx[3] = Acc  # Vel_descent

    return dx

class Simulator:
    def __init__(self, vel_wind, angle_wind, result_dir, multi_mode=False):
        self.vel_wind = vel_wind
        self.angle_wind = angle_wind
        self.result_dir = result_dir
        self.multi_mode = multi_mode

        # ランチクリア値、計算中に記録
        self.acc_launch_clear = 0.0
        self.vel_launch_clear = 0.0

    def simulation(self, rocket):
        length = (rocket.L - rocket.Lcg0) * np.cos(np.deg2rad(rocket.elevation0))
        X0_ENU = length * np.cos(np.deg2rad(rocket.azimuth0))
        Y0_ENU = length * np.sin(np.deg2rad(rocket.azimuth0))
        Z0_ENU = (rocket.L - rocket.Lcg0) * np.sin(np.deg2rad(np.abs(rocket.elevation0)))
        self.Pos0_ENU = np.array([X0_ENU, Y0_ENU, Z0_ENU])
        self.quat0 = coord.euler2quat(rocket.azimuth0, rocket.elevation0, rocket.roll0)
        zero_array = np.array([[0.0] * 3])

        x0 = np.zeros(18)
        x0[0:3] = self.Pos0_ENU
        x0[3:6] = zero_array  # Vel_ENU
        x0[6:9] = zero_array  # Vel_Body
        x0[9:12] =  zero_array  # omega_Body
        x0[12:16] = self.quat0  # quat
        x0[16] = rocket.m0_f  # mf
        x0[17] = rocket.m0_ox  # mox
        start_time = 0.0
        def estimate_end():
            It_digits = len(str(rocket.total_impulse))
            return rocket.total_impulse / (10 ** (It_digits - 5)) * 1.5
        end_time = estimate_end() if rocket.auto_end else rocket.end_time
        time = np.arange(start_time, end_time, rocket.timestep)
        ode_log = odeint(dynamics, x0, time, args=(rocket, self))

        self.time_log = time
        self.Pos_ENU_log = ode_log[:, 0:3]
        self.Vel_ENU_log = ode_log[:, 3:6]
        self.Vel_Body_log = ode_log[:, 6:9]
        self.omega_log = ode_log[:, 9:12]
        self.quat_log = ode_log[:, 12:16]
        self.mf_log = ode_log[:, 16]
        self.mox_log = ode_log[:, 17]
        self.post_process(rocket)

    def post_process(self, rocket):
        # 着地後の分をカット
        index_hard_landing = np.argmax(self.Pos_ENU_log[:, 2] <= 0.0)
        self.time_log = self.time_log[:index_hard_landing+1]
        self.Pos_ENU_log = self.Pos_ENU_log[:index_hard_landing+1, :]
        self.Vel_ENU_log = self.Vel_ENU_log[:index_hard_landing+1, :]
        self.Vel_Body_log = self.Vel_Body_log[:index_hard_landing+1, :]
        self.omega_log = self.omega_log[:index_hard_landing+1, :]
        self.quat_log = self.quat_log[:index_hard_landing+1, :]
        self.quat_log = np.array(list(map(coord.quat_normalize, self.quat_log)))
        self.mf_log = self.mf_log[:index_hard_landing+1]
        self.mox_log = self.mox_log[:index_hard_landing+1]

        # あとから計算
        altitude_log = self.Pos_ENU_log[:, 2]
        downrange_log = np.array(list(map(np.linalg.norm, self.Pos_ENU_log[:, 0:2])))
        self.g_log = np.array(list(map(env.gravity, altitude_log)))
        self.P_air_log = env.get_std_press_array(altitude_log)
        self.rho_air_log = env.get_std_density_array(altitude_log)
        self.mp_log = self.mox_log + self.mf_log
        self.m_log = self.mp_log + rocket.ms

        DCM_ENU2Body_log = np.array(list(map(coord.DCM_ENU2Body_quat, self.quat_log)))
        self.wind_ENU_log = np.array([env.Wind_ENU(self.vel_wind, self.angle_wind, alt, rocket.Wind_refAltitude, rocket.Wind_power_exp) for alt in altitude_log])
        self.Vel_air_log = np.array([DCM.dot(vel - wind) for DCM, vel, wind in zip(DCM_ENU2Body_log, self.Vel_ENU_log, self.wind_ENU_log)])
        self.Vel_air_abs_log = np.array(list(map(np.linalg.norm, self.Vel_air_log)))
        self.alpha_log = np.rad2deg(np.arctan2(self.Vel_air_log[:, 2], self.Vel_air_log[:, 0]))
        self.beta_log = np.rad2deg(np.arcsin(self.Vel_air_log[:, 1] / self.Vel_air_abs_log))
        self.Mach_log = self.Vel_air_abs_log / env.get_std_soundspeed_array(altitude_log)
        self.dynamic_pressure_log = 0.5 * self.rho_air_log * self.Vel_air_abs_log * self.Vel_air_abs_log
        attitude_log = np.array(list(map(coord.quat2euler, DCM_ENU2Body_log)))
        self.azimuth_log = attitude_log[:, 0]
        self.elevation_log = attitude_log[:, 1]
        self.roll_log = attitude_log[:, 2]
        thrust_SL_log = rocket.thrust(self.time_log)        
        self.mdot_p_log = thrust_SL_log / (rocket.Isp * 9.80665)
        self.mdot_f_log = rocket.mdot_f * np.array([thrust > 0.0 for thrust in rocket.thrust(self.time_log)])
        self.mdot_ox_log = self.mdot_p_log - self.mdot_f_log
        pressure_thrust_log = (self.P_air_log[0] - self.P_air_log) * rocket.Ae
        self.thrust_log = np.array([thrust_SL + pressure_thrust if thrust_SL > 0.0 else 0.0 for thrust_SL, pressure_thrust in zip(thrust_SL_log, pressure_thrust_log)]) 
        self.Isp_log = rocket.Isp + np.array([pressure_thrust / (mdot_p * 9.80665) if mdot_p > 0.0 else 0.0 for pressure_thrust, mdot_p in zip(pressure_thrust_log, self.mdot_p_log)])
        self.drag_log = self.dynamic_pressure_log * rocket.Cd(self.Mach_log) * rocket.A
        self.normal_log = self.dynamic_pressure_log * rocket.CNa(self.Mach_log) * rocket.A
        self.Force_log = np.c_[self.thrust_log - self.drag_log, self.normal_log * self.beta_log, -self.normal_log * self.alpha_log]
        self.Acc_Body_log = np.array([Force / m + DCM.dot(g) for Force, m, DCM, g in zip(self.Force_log, self.m_log, DCM_ENU2Body_log, np.c_[np.zeros_like(self.g_log), np.zeros_like(self.g_log), -self.g_log])])
        self.Lcg_ox_log = rocket.L - (rocket.L_motor + (self.mox_log / rocket.m0_ox) * (rocket.Lcg0_ox - rocket.L_motor))
        self.Lcg_p_log = (self.mf_log * rocket.Lcg_f + self.mox_log * self.Lcg_ox_log) / self.mp_log
        self.Lcg_log = (self.mp_log * self.Lcg_p_log + rocket.ms * rocket.Lcg_s) / self.m_log
        self.Lcp_log = rocket.Lcp(self.Mach_log)
        self.Fst_log = (self.Lcp_log - self.Lcg_log) / rocket.L * 100  # [%]

        #  イベントでの値
        # apogee
        index_apogee = np.argmax(altitude_log)
        self.time_apogee = self.time_log[index_apogee]
        self.altitude_apogee = altitude_log[index_apogee]
        self.Pos_ENU_apogee = self.Pos_ENU_log[index_apogee, :]
        self.Vel_ENU_apogee = self.Vel_ENU_log[index_apogee, :]
        self.Vel_air_abs_apogee = self.Vel_air_abs_log[index_apogee]
        self.m_apogee = self.m_log[index_apogee]
        self.downrange_apogee = np.linalg.norm(self.Pos_ENU_apogee[0:2])
        # Max Speed
        index_vel_max = np.argmax(self.Vel_air_abs_log[:index_apogee])
        self.time_vel_max = self.time_log[index_vel_max]
        self.altitude_vel_max = altitude_log[index_vel_max]
        self.Vel_air_max = self.Vel_air_abs_log[index_vel_max]

        # Max Mach Number
        index_Mach_max = np.argmax(self.Mach_log[:index_apogee])
        self.time_Mach_max = self.time_log[index_Mach_max]
        self.altitude_Mach_max = altitude_log[index_Mach_max]
        self.Mach_max = self.Mach_log[index_Mach_max]

        # Max Q
        index_maxQ = np.argmax(self.dynamic_pressure_log[:index_apogee])
        self.time_maxQ = self.time_log[index_maxQ]
        self.altitude_maxQ = altitude_log[index_maxQ]
        self.maxQ = self.dynamic_pressure_log[index_maxQ]

        # Hard Landing
        self.time_hard_landing = self.time_log[-1]
        self.hard_landing_point = self.Pos_ENU_log[-1, 0:2]
        self.downrange_hard_landing = np.linalg.norm(self.hard_landing_point)

        #  パラシュート降下
        x0 = np.zeros(4)
        x0[0:3] = self.Pos_ENU_apogee
        x0[3] = self.Vel_ENU_apogee[2]
        est_landing = self.altitude_apogee / np.sqrt(2.0 * self.m_apogee * env.gravity(0.0) / (env.get_std_density(0.0) * (rocket.CdS1 + rocket.CdS2)))
        time = np.arange(self.time_hard_landing, self.time_hard_landing+est_landing, 0.1)
        ode_log = odeint(parachute_dynamics, x0, time, args=(rocket, self))

        index_sepa2 = np.argmax(ode_log[:, 2] <= rocket.alt_sepa2)
        index_soft_landing = np.argmax(ode_log[:, 2] <= 0.0)
        self.time_sepa2 = time[index_sepa2]
        self.time_soft_landing = time[index_soft_landing]
        self.soft_landing_point = ode_log[index_soft_landing, 0:2]
        self.downrange_soft_landing = np.linalg.norm(self.soft_landing_point)

        self.landing_points = [self.hard_landing_point, self.soft_landing_point]

        if self.multi_mode:
            return

        txt = open(self.result_dir + '/result.txt', mode='w')
        txt.writelines(['Launcher Clear Acceleration,', str(round(self.acc_launch_clear / 9.80665, 3)), '[G]\n'])
        txt.writelines(['Launcher Clear Velocity,', str(round(self.vel_launch_clear, 3)), '[m/s]\n'])
        txt.writelines(['Max Q X+,', str(round(self.time_maxQ, 3)), '[s]\n'])
        txt.writelines(['Max Q Altitude,', str(round(self.altitude_maxQ / 1000.0, 3)), '[km]\n'])
        txt.writelines(['Max Q,', str(round(self.maxQ / 1000.0, 3)), '[kPa]\n'])
        txt.writelines(['Max Speed X+,', str(round(self.time_vel_max,3)), '[s]\n'])
        txt.writelines(['Max Speed Altitude,', str(round(self.altitude_vel_max / 1000.0, 3)), '[km]\n'])
        txt.writelines(['Max Speed,', str(round(self.Vel_air_max, 3)), '[m/s]\n'])
        txt.writelines(['Max Mach Number X+,', str(round(self.time_Mach_max, 3)), '[s]\n'])
        txt.writelines(['Max Mach Number Altitude,', str(round(self.altitude_Mach_max / 1000.0, 3)), '[km]\n'])
        txt.writelines(['Max Mach Number,', str(round(self.Mach_max, 3)), '[-]\n'])
        txt.writelines(['Apogee X+,', str(round(self.time_apogee, 3)), '[s]\n'])
        txt.writelines(['Apogee Altitude,', str(round(self.altitude_apogee / 1000.0, 3)), '[km]\n'])
        txt.writelines(['Apogee Downrange,', str(round(self.downrange_apogee / 1000.0, 3)), '[km]\n'])
        txt.writelines(['Apogee Air Velocity,', str(round(self.Vel_air_abs_apogee, 3)), '[m/s]\n'])
        txt.writelines(['Hard Landing X+,', str(round(self.time_hard_landing, 3)), '[s]\n'])
        txt.writelines(['Hard Landing Downrange,', str(round(self.downrange_hard_landing / 1000.0, 3)), '[km]\n'])
        txt.writelines(['2nd Parachute Opening X+,', str(round(self.time_sepa2, 3)), '[s]\n'])
        txt.writelines(['Soft Landing X+,', str(round(self.time_soft_landing, 3)), '[s]\n'])
        txt.writelines(['Soft Landing Downrange,', str(round(self.downrange_soft_landing / 1000.0, 3)), '[km]\n'])
        txt.close()

        output_array = np.c_[
            self.time_log,
            self.g_log,
            self.P_air_log,
            self.rho_air_log,
            self.wind_ENU_log,
            self.mdot_f_log,
            self.mdot_ox_log,
            self.mdot_p_log,
            self.mf_log,
            self.mox_log,
            self.mp_log,
            self.m_log,
            self.Lcg_ox_log,
            self.Lcg_p_log,
            self.Lcg_log,
            self.Lcp_log,
            self.Fst_log,
            self.alpha_log,
            self.beta_log,
            self.omega_log,
            self.quat_log,
            self.azimuth_log,
            self.elevation_log,
            self.roll_log,
            self.thrust_log,
            self.Isp_log,
            self.drag_log,
            self.normal_log,
            self.Force_log,
            self.Vel_air_log,
            self.Vel_air_abs_log,
            self.dynamic_pressure_log,
            self.Mach_log,
            self.Acc_Body_log,
            self.Vel_Body_log,
            self.Vel_ENU_log,
            self.Pos_ENU_log,
        ]
        header = 'time,g,P_air,rho_air,wind_East,wind_North,wind_Up,mdot_f,mdot_ox,mdot_p,mf,mox,mp,m,Lcg_ox,Lcg_p,Lcg,Lcp,Fst,alpha,beta,omega_roll,omega_pitch,omega_yaw,quat0,quat1,quat2,quat3,azimuth,elevation,roll,thrust,Isp,drag,normal,Force_X,Force_Y,Force_Z,Vel_air_X,Vel_air_Y,Vel_air_Z,Vel_air_abs,dynamic_pressure,Mach,Acc_Body_X,Acc_Body_Y,Acc_Body_Z,Vel_Body_X,Vel_Body_Y,Vel_Body_Z,Vel_East,Vel_North,Vel_Up,Pos_East,Pos_North,Pos_Up'
        np.savetxt(self.result_dir + '/log.csv', output_array, delimiter=',', header=header)

        plt.close('all')

        plt.figure('Mass')
        plt.plot(self.time_log, self.mf_log, label='mass fuel')
        plt.plot(self.time_log, self.mox_log, label='mass oxidizer')
        plt.plot(self.time_log, self.m_log, label='mass all')
        plt.xlabel('Time [sec]')
        plt.ylabel('Mass [kg]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/Mass.png')

        plt.figure('C.G./C.P.')
        plt.plot(self.time_log, (self.Lcg_log / rocket.L) * 100.0, label='C.G.')
        plt.plot(self.time_log, (self.Lcp_log / rocket.L) * 100.0, label='C.P.')
        plt.xlabel('Time [sec]')
        plt.ylabel('From Nose [%]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/CG_CP.png')

        plt.figure('Attitude')
        plt.plot(self.time_log, self.azimuth_log, label='azimuth')
        plt.plot(self.time_log, self.elevation_log, label='elevation')
        plt.plot(self.time_log, self.roll_log, label='roll')
        plt.plot(self.time_log, np.rad2deg(self.alpha_log), label='alpha')
        plt.plot(self.time_log, np.rad2deg(self.beta_log), label='beta')
        plt.xlabel('Time [sec]')
        plt.ylabel('Attitude [deg]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/Attitude.png')

        plt.figure('Force')
        plt.plot(self.time_log, self.thrust_log, label='thrust')
        plt.plot(self.time_log, self.drag_log, label='drag')
        plt.plot(self.time_log, self.normal_log, label='normal')
        plt.xlabel('Time [sec]')
        plt.ylabel('Force [N]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/Force.png')

        plt.figure('Air Velocity')
        plt.plot(self.time_log, self.Vel_air_log[:, 0], label='V_air X')
        plt.plot(self.time_log, self.Vel_air_log[:, 1], label='V_air Y')
        plt.plot(self.time_log, self.Vel_air_log[:, 2], label='V_air Z')
        plt.xlabel('Time [sec]')
        plt.ylabel('Air Velocity [m/s]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/VelocityAir.png')

        plt.figure('Mach Number')
        plt.plot(self.time_log, self.Mach_log, label='Mach number')
        plt.xlabel('Time [sec]')
        plt.ylabel('Mach Number [-]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/Mach.png')

        plt.figure('Dynamic Pressure')
        plt.plot(self.time_log, self.dynamic_pressure_log / 1000.0, label='dynamic pressure')
        plt.xlabel('Time [sec]')
        plt.ylabel('Dynamic Pressure [kPa]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/Dynamicpressure.png')

        plt.figure('Body Acceleration')
        plt.plot(self.time_log, self.Acc_Body_log[:, 0], label='Acc_Body X')
        plt.plot(self.time_log, self.Acc_Body_log[:, 1], label='Acc_Body Y')
        plt.plot(self.time_log, self.Acc_Body_log[:, 2], label='Acc_Body Z')
        plt.xlabel('Time [sec]')
        plt.ylabel('Body Acceleration [m/s^2]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/AccelerationBody.png')

        plt.figure('Body Velocity')
        plt.plot(self.time_log, self.Vel_Body_log[:, 0], label='V_Body X')
        plt.plot(self.time_log, self.Vel_Body_log[:, 1], label='V_Body Y')
        plt.plot(self.time_log, self.Vel_Body_log[:, 2], label='V_Body Z')
        plt.xlabel('Time [sec]')
        plt.ylabel('Body Velocity [m/s]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/VelocityBody.png')

        plt.figure('ENU Velocity')
        plt.plot(self.time_log, self.Vel_ENU_log[:, 0], label='V_East')
        plt.plot(self.time_log, self.Vel_ENU_log[:, 1], label='V_North ')
        plt.plot(self.time_log, self.Vel_ENU_log[:, 2], label='V_Up ')
        plt.xlabel('Time [sec]')
        plt.ylabel('ENU Velocity [m/s]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/VelocityENU.png')

        plt.figure('ENU Position')
        plt.plot(self.time_log, self.Vel_ENU_log[:, 0] / 1000.0, label='Pos_East')
        plt.plot(self.time_log, self.Vel_ENU_log[:, 1] / 1000.0, label='Pos_North')
        plt.plot(self.time_log, self.Vel_ENU_log[:, 2] / 1000.0, label='Pos_Up')
        plt.xlabel('Time [sec]')
        plt.ylabel('ENU Position [km]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/PositionENU.png')

        plt.figure('Trajectory')
        plt.plot(downrange_log / 1000.0, altitude_log / 1000.0)
        plt.xlabel('Downrange [km]')
        plt.ylabel('Altitude [km]')
        plt.grid()
        plt.legend()
        plt.savefig(self.result_dir + '/Trajectory.png')


class WindMapper:
    # 継承していないがSimulatorクラスとスイッチングされるクラス
    # simulationメソッドは共通の引数であること
    def __init__(self, result_dir):
        self.result_dir = result_dir
        self.Vel_wind_min = 1.0
        self.Vel_wind_max = 7.0
        self.angle_wind_min = 0.0  # [deg]
        self.angle_wind_max = 360.0

        self.Vel_wind_array = np.arange(self.Vel_wind_min, self.Vel_wind_max+1.0, 1.0)
        self.angle_wind_array = np.arange(self.angle_wind_min, self.angle_wind_max, 45.0)

    def simulation(self, rocket):
        self.landing_points = []
        for Vel_wind in self.Vel_wind_array:
            points = []
            for angle_wind in self.angle_wind_array:
                simulator = Simulator(Vel_wind, angle_wind, self.result_dir, True)
                simulator.simulation()
                points.append(simulator.landing_points)

            points.append(points[0])  # 分散を閉じるため
            self.landing_points.append(points)


