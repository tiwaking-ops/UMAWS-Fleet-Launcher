import sys
sys.path.insert(0, 'src')
import pmk
print('pmk:', pmk.__file__)
try:
    import cna
    print('cna:', cna.__file__)
except Exception as e:
    print('cna import error:', e)
