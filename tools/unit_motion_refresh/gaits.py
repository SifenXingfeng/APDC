"""Locomotion convention: forward is -Y; planted feet travel +Y in body space."""
import math

GROUND_MODELS = ['APDC_b2_automaton', 'APDC_b2_multipod', 'APDC_b2_doomdog',
                 'APDC_b2_aa02', 'APDC_f1_multipod_artillery', 'APDC_f1_nyto_final']


def foot_path(time, phase=0., stride=.72, lift=.24, duty=.60):
    """Return body-space y/z offsets and contact. Phase is measured in cycles.

    Stance has constant positive Y velocity. Swing returns towards -Y.
    A Hermite swing preserves velocity at lift-off/touchdown, avoiding snaps.
    """
    p = (time + phase) % 1.
    if p < duty:
        return stride * (p / duty - .5), 0., True
    u = (p - duty) / (1. - duty)
    tangent = stride * (1. - duty) / duty
    y = stride * .5 * (4*u**3 - 6*u**2 + 1) + tangent * (2*u**3 - 3*u**2 + u)
    return y, lift * math.sin(math.pi*u)**2, False


def assign_alternating(legs):
    """Bipeds alternate; quadrupeds use diagonals; hexapods alternating tripods.

    Sort by real hip position, never by bone traversal order or bone numbering.
    """
    sides = [[leg for leg in legs if (leg['hip'][0] > 0) == positive]
             for positive in (False, True)]
    assert len(sides[0]) == len(sides[1]) and len(sides[0]) in (1, 2, 3)
    for side, members in enumerate(sides):
        for rank, leg in enumerate(sorted(members, key=lambda x: x['hip'][1])):
            leg['phase'] = ((rank + side) % 2) * .5
            leg['longitudinal_rank'] = rank
            leg['side'] = side
    return legs


def settings(ident):
    if ident == 'APDC_ump_chibi':
        return dict(stride=.88, lift=.40, duty=.42, frames=21)
    return dict(stride=.72, lift=.24, duty=.60, frames=31)


if __name__ == '__main__':
    for duty in (.42, .60):
        for i in range(1000):
            t=i/1000
            y,z,contact=foot_path(t,duty=duty)
            if contact and t < duty-.001:
                yn,_,_=foot_path(t+.0001,duty=duty)
                assert yn > y, 'Grounded foot slides forward: reversed walk!'
            assert z >= 0
        assert abs(foot_path(1e-7,duty=duty)[0]-foot_path(1-1e-7,duty=duty)[0]) < 1e-5
    for count in (2,4,6):
        legs=[{'hip':(side,j,1)} for side in (-1,1) for j in range(count//2)]
        assign_alternating(legs)
        assert sum(l['phase']==0 for l in legs)==count//2
        for j in range(count//2):assert legs[j]['phase'] != legs[j+count//2]['phase']
        if count>2:
            for side in (0,1):
                group=[l for l in legs if l['side']==side]
                assert all(a['phase']!=b['phase'] for a,b in zip(group,group[1:]))
    print('GAIT_MATH_PASS')
