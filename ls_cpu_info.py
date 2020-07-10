import os, sys
import platform
import multiprocessing
IS_PY2 = sys.version_info[0] == 2


class DataSource(object):
    bits = platform.architecture()[0]
    cpu_count = multiprocessing.cpu_count()
    is_windows = platform.system().lower() == 'windows'
    arch_string_raw = platform.machine()
    uname_string_raw = platform.uname()[5]
    can_cpuid = True

    @staticmethod
    def has_proc_cpuinfo():
        return os.path.exists('/proc/cpuinfo')

    @staticmethod
    def has_dmesg():
        return len(_program_paths('dmesg')) > 0

    @staticmethod
    def has_var_run_dmesg_boot():
        uname = platform.system().strip().strip('"').strip("'").strip().lower()
        return 'linux' in uname and os.path.exists('/var/run/dmesg.boot')

    @staticmethod
    def has_cpufreq_info():
        return len(_program_paths('cpufreq-info')) > 0

    @staticmethod
    def has_sestatus():
        return len(_program_paths('sestatus')) > 0

    @staticmethod
    def has_sysctl():
        return len(_program_paths('sysctl')) > 0

    @staticmethod
    def has_isainfo():
        return len(_program_paths('isainfo')) > 0

    @staticmethod
    def has_kstat():
        return len(_program_paths('kstat')) > 0

    @staticmethod
    def has_sysinfo():
        uname = platform.system().strip().strip('"').strip("'").strip().lower()
        is_beos = 'beos' in uname or 'haiku' in uname
        return is_beos and len(_program_paths('sysinfo')) > 0

    @staticmethod
    def has_lscpu():
        return len(_program_paths('lscpu')) > 0

    @staticmethod
    def has_ibm_pa_features():
        return len(_program_paths('lsprop')) > 0

    @staticmethod
    def has_wmic():
        returncode, output = _run_and_get_stdout(['wmic', 'os', 'get', 'Version'])
        return returncode == 0 and len(output) > 0

    @staticmethod
    def cat_proc_cpuinfo():
        return _run_and_get_stdout(['cat', '/proc/cpuinfo'])

    @staticmethod
    def cpufreq_info():
        return _run_and_get_stdout(['cpufreq-info'])

    @staticmethod
    def sestatus_b():
        return _run_and_get_stdout(['sestatus', '-b'])

    @staticmethod
    def dmesg_a():
        return _run_and_get_stdout(['dmesg', '-a'])

    @staticmethod
    def cat_var_run_dmesg_boot():
        return _run_and_get_stdout(['cat', '/var/run/dmesg.boot'])

    @staticmethod
    def sysctl_machdep_cpu_hw_cpufrequency():
        return _run_and_get_stdout(['sysctl', 'machdep.cpu', 'hw.cpufrequency'])

    @staticmethod
    def isainfo_vb():
        return _run_and_get_stdout(['isainfo', '-vb'])

    @staticmethod
    def kstat_m_cpu_info():
        return _run_and_get_stdout(['kstat', '-m', 'cpu_info'])

    @staticmethod
    def sysinfo_cpu():
        return _run_and_get_stdout(['sysinfo', '-cpu'])

    @staticmethod
    def lscpu():
        return _run_and_get_stdout(['lscpu'])

    @staticmethod
    def ibm_pa_features():
        import glob

        ibm_features = glob.glob('/proc/device-tree/cpus/*/ibm,pa-features')
        if ibm_features:
            return _run_and_get_stdout(['lsprop', ibm_features[0]])


def _parse_arch(arch_string_raw):
    import re

    arch, bits = None, None
    arch_string_raw = arch_string_raw.lower()

    # X86
    if re.match(r'^i\d86$|^x86$|^x86_32$|^i86pc$|^ia32$|^ia-32$|^bepc$', arch_string_raw):
        arch = 'X86_32'
        bits = 32
    elif re.match(r'^x64$|^x86_64$|^x86_64t$|^i686-64$|^amd64$|^ia64$|^ia-64$', arch_string_raw):
        arch = 'X86_64'
        bits = 64
    # ARM
    elif re.match(r'^armv8-a|aarch64$', arch_string_raw):
        arch = 'ARM_8'
        bits = 64
    elif re.match(r'^armv7$|^armv7[a-z]$|^armv7-[a-z]$|^armv6[a-z]$', arch_string_raw):
        arch = 'ARM_7'
        bits = 32
    elif re.match(r'^armv8$|^armv8[a-z]$|^armv8-[a-z]$', arch_string_raw):
        arch = 'ARM_8'
        bits = 32
    # PPC
    elif re.match(r'^ppc32$|^prep$|^pmac$|^powermac$', arch_string_raw):
        arch = 'PPC_32'
        bits = 32
    elif re.match(r'^powerpc$|^ppc64$|^ppc64le$', arch_string_raw):
        arch = 'PPC_64'
        bits = 64
    # SPARC
    elif re.match(r'^sparc32$|^sparc$', arch_string_raw):
        arch = 'SPARC_32'
        bits = 32
    elif re.match(r'^sparc64$|^sun4u$|^sun4v$', arch_string_raw):
        arch = 'SPARC_64'
        bits = 64
    # S390X
    elif re.match(r'^s390x$', arch_string_raw):
        arch = 'S390X'
        bits = 64

    return (arch, bits)


    
def _program_paths(program_name):
    paths = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ['PATH']
    for p in os.environ['PATH'].split(os.pathsep):
        p = os.path.join(p, program_name)
        if os.access(p, os.X_OK):
            paths.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, os.X_OK):
                paths.append(pext)
    return paths

def _run_and_get_stdout(command, pipe_command=None):
    from subprocess import Popen, PIPE

    if not pipe_command:
        p1 = Popen(command, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        output = p1.communicate()[0]
        if not IS_PY2:
            output = output.decode(encoding='UTF-8')
        return p1.returncode, output
    else:
        p1 = Popen(command, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        p2 = Popen(pipe_command, stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
        p1.stdout.close()
        output = p2.communicate()[0]
        if not IS_PY2:
            output = output.decode(encoding='UTF-8')
        return p2.returncode, output

def _get_field(cant_be_number, raw_string, convert_to, default_value, *field_names):
    retval = _get_field_actual(cant_be_number, raw_string, field_names)

    # Convert the return value
    if retval and convert_to:
        try:
            retval = convert_to(retval)
        except:
            retval = default_value

    # Return the default if there is no return value
    if retval is None:
        retval = default_value

    return retval

def _to_decimal_string(ticks):
    try:
        # Convert to string
        ticks = '{0}'.format(ticks)

        # Strip off non numbers and decimal places
        ticks = "".join(n for n in ticks if n.isdigit() or n=='.').strip()
        if ticks == '':
            ticks = '0'

        # Add decimal if missing
        if '.' not in ticks:
            ticks = '{0}.0'.format(ticks)

        # Remove trailing zeros
        ticks = ticks.rstrip('0')

        # Add one trailing zero for empty right side
        if ticks.endswith('.'):
            ticks = '{0}0'.format(ticks)

        # Make sure the number can be converted to a float
        ticks = float(ticks)
        ticks = '{0}'.format(ticks)
        return ticks
    except:
        return '0.0'

def _get_field_actual(cant_be_number, raw_string, field_names):
    for line in raw_string.splitlines():
        for field_name in field_names:
            field_name = field_name.lower()
            if ':' in line:
                left, right = line.split(':', 1)
                left = left.strip().lower()
                right = right.strip()
                if left == field_name and len(right) > 0:
                    if cant_be_number:
                        if not right.isdigit():
                            return right
                    else:
                        return right

    return None

def _parse_cpu_brand_string(cpu_string):
    # Just return 0 if the processor brand does not have the Hz
    if not 'hz' in cpu_string.lower():
        return ('0.0', 0)

    hz = cpu_string.lower()
    scale = 0

    if hz.endswith('mhz'):
        scale = 6
    elif hz.endswith('ghz'):
        scale = 9
    if '@' in hz:
        hz = hz.split('@')[1]
    else:
        hz = hz.rsplit(None, 1)[1]

    hz = hz.rstrip('mhz').rstrip('ghz').strip()
    hz = _to_decimal_string(hz)

    return (hz, scale)

def _hz_short_to_full(ticks, scale):
    try:
        # Make sure the number can be converted to a float
        ticks = float(ticks)
        ticks = '{0}'.format(ticks)

        # Scale the numbers
        hz = ticks.lstrip('0')
        old_index = hz.index('.')
        hz = hz.replace('.', '')
        hz = hz.ljust(scale + old_index+1, '0')
        new_index = old_index + scale
        hz = '{0}.{1}'.format(hz[:new_index], hz[new_index:])
        left, right = hz.split('.')
        left, right = int(left), int(right)
        return (left, right)
    except:
        return (0, 0)

def _hz_short_to_friendly(ticks, scale):
    try:
        # Get the raw Hz as a string
        left, right = _hz_short_to_full(ticks, scale)
        result = '{0}.{1}'.format(left, right)

        # Get the location of the dot, and remove said dot
        dot_index = result.index('.')
        result = result.replace('.', '')

        # Get the Hz symbol and scale
        symbol = "Hz"
        scale = 0
        if dot_index > 9:
            symbol = "GHz"
            scale = 9
        elif dot_index > 6:
            symbol = "MHz"
            scale = 6
        elif dot_index > 3:
            symbol = "KHz"
            scale = 3

        # Get the Hz with the dot at the new scaled point
        result = '{0}.{1}'.format(result[:-scale-1], result[-scale-1:])

        # Format the ticks to have 4 numbers after the decimal
        # and remove any superfluous zeroes.
        result = '{0:.4f} {1}'.format(float(result), symbol)
        result = result.rstrip('0')
        return result
    except:
        return '0.0000 Hz'
    
def _friendly_bytes_to_int(friendly_bytes):
    input = friendly_bytes.lower()

    formats = {
        'gb' : 1024 * 1024 * 1024,
        'mb' : 1024 * 1024,
        'kb' : 1024,

        'g' : 1024 * 1024 * 1024,
        'm' : 1024 * 1024,
        'k' : 1024,
        'b' : 1,
    }

    try:
        for pattern, multiplier in formats.items():
            if input.endswith(pattern):
                return int(input.split(pattern)[0].strip()) * multiplier

    except Exception as err:
        pass

    return friendly_bytes

def _filter_dict_keys_with_empty_values(info):
    # Filter out None, 0, "", (), {}, []
    #info = {k: v for k, v in info.items() if v}

    # Filter out (0, 0)
    info = {k: v for k, v in info.items() if v != (0, 0)}

    # Filter out strings that start with "0.0"
    info = {k: v for k, v in info.items() if not (type(v) == str and v.startswith('0.0'))}

    return info

def _get_cpu_info_from_proc_cpuinfo():
    '''
    Returns the CPU info gathered from /proc/cpuinfo.
    Returns {} if /proc/cpuinfo is not found.
    '''
    try:
        # Just return {} if there is no cpuinfo
        if not DataSource.has_proc_cpuinfo():
            return {}

        returncode, output = DataSource.cat_proc_cpuinfo()
        if returncode != 0:
            return {}

        # Various fields
        vendor_id = _get_field(False, output, None, '', 'vendor_id', 'vendor id', 'vendor')
        processor_brand = _get_field(True, output, None, None, 'model name','cpu', 'processor')
        cache_size = _get_field(False, output, None, '', 'cache size')
        stepping = _get_field(False, output, int, 0, 'stepping')
        model = _get_field(False, output, int, 0, 'model')
        family = _get_field(False, output, int, 0, 'cpu family')
        hardware = _get_field(False, output, None, '', 'Hardware')

        # Flags
        flags = _get_field(False, output, None, None, 'flags', 'Features')
        if flags:
            flags = flags.split()
            flags.sort()

        # Check for other cache format
        if not cache_size:
            try:
                for i in range(0, 10):
                    name = "cache{0}".format(i)
                    value = _get_field(False, output, None, None, name)
                    if value:
                        value = [entry.split('=') for entry in value.split(' ')]
                        value = dict(value)
                        if 'level' in value and value['level'] == '3' and 'size' in value:
                            cache_size = value['size']
                            break
            except Exception:
                pass

        # Convert from MHz string to Hz
        hz_actual = _get_field(False, output, None, '', 'cpu MHz', 'cpu speed', 'clock', 'cpu MHz dynamic', 'cpu MHz static')
        hz_actual = hz_actual.lower().rstrip('mhz').strip()
        hz_actual = _to_decimal_string(hz_actual)

        # Convert from GHz/MHz string to Hz
        hz_advertised, scale = (None, 0)
        try:
            hz_advertised, scale = _parse_cpu_brand_string(processor_brand)
        except Exception:
            pass

        info = {
        'hardware_raw' : hardware,
        'brand_raw' : processor_brand,

        'l3_cache_size' : _friendly_bytes_to_int(cache_size),
        'flags' : flags,
        'vendor_id_raw' : vendor_id,
        'stepping' : stepping,
        'model' : model,
        'family' : family,
        }

        # Make the Hz the same for actual and advertised if missing any
        if not hz_advertised or hz_advertised == '0.0':
            hz_advertised = hz_actual
            scale = 6
        elif not hz_actual or hz_actual == '0.0':
            hz_actual = hz_advertised

        # Add the Hz if there is one
        if _hz_short_to_full(hz_advertised, scale) > (0, 0):
            info['hz_advertised_friendly'] = _hz_short_to_friendly(hz_advertised, scale)
            info['hz_advertised'] = _hz_short_to_full(hz_advertised, scale)
        if _hz_short_to_full(hz_actual, scale) > (0, 0):
            info['hz_actual_friendly'] = _hz_short_to_friendly(hz_actual, 6)
            info['hz_actual'] = _hz_short_to_full(hz_actual, 6)

        return info
    except:
        #raise # NOTE: To have this throw on error, uncomment this line
        return {}

def _get_cpu_info_from_lscpu():
    '''
    Returns the CPU info gathered from lscpu.
    Returns {} if lscpu is not found.
    '''
    try:
        if not DataSource.has_lscpu():
            return {}

        returncode, output = DataSource.lscpu()
        if returncode != 0:
            return {}

        info = {}

        new_hz = _get_field(False, output, None, None, 'CPU max MHz', 'CPU MHz')
        if new_hz:
            new_hz = _to_decimal_string(new_hz)
            scale = 6
            info['hz_advertised_friendly'] = _hz_short_to_friendly(new_hz, scale)
            info['hz_actual_friendly'] = _hz_short_to_friendly(new_hz, scale)
            info['hz_advertised'] = _hz_short_to_full(new_hz, scale)
            info['hz_actual'] = _hz_short_to_full(new_hz, scale)

        new_hz = _get_field(False, output, None, None, 'CPU dynamic MHz', 'CPU static MHz')
        if new_hz:
            new_hz = _to_decimal_string(new_hz)
            scale = 6
            info['hz_advertised_friendly'] = _hz_short_to_friendly(new_hz, scale)
            info['hz_actual_friendly'] = _hz_short_to_friendly(new_hz, scale)
            info['hz_advertised'] = _hz_short_to_full(new_hz, scale)
            info['hz_actual'] = _hz_short_to_full(new_hz, scale)

        vendor_id = _get_field(False, output, None, None, 'Vendor ID')
        if vendor_id:
            info['vendor_id_raw'] = vendor_id

        brand = _get_field(False, output, None, None, 'Model name')
        if brand:
            info['brand_raw'] = brand

        family = _get_field(False, output, None, None, 'CPU family')
        if family and family.isdigit():
            info['family'] = int(family)

        stepping = _get_field(False, output, None, None, 'Stepping')
        if stepping and stepping.isdigit():
            info['stepping'] = int(stepping)

        model = _get_field(False, output, None, None, 'Model')
        if model and model.isdigit():
            info['model'] = int(model)

        l1_data_cache_size = _get_field(False, output, None, None, 'L1d cache')
        if l1_data_cache_size:
            info['l1_data_cache_size'] = _friendly_bytes_to_int(l1_data_cache_size)

        l1_instruction_cache_size = _get_field(False, output, None, None, 'L1i cache')
        if l1_instruction_cache_size:
            info['l1_instruction_cache_size'] = _friendly_bytes_to_int(l1_instruction_cache_size)

        l2_cache_size = _get_field(False, output, None, None, 'L2 cache', 'L2d cache')
        if l2_cache_size:
            info['l2_cache_size'] = _friendly_bytes_to_int(l2_cache_size)

        l3_cache_size = _get_field(False, output, None, None, 'L3 cache')
        if l3_cache_size:
            info['l3_cache_size'] = _friendly_bytes_to_int(l3_cache_size)

        # Flags
        flags = _get_field(False, output, None, None, 'flags', 'Features')
        if flags:
            flags = flags.split()
            flags.sort()
            info['flags'] = flags
        return info
    except:
        return {}

def _copy_new_fields(info, new_info):
    keys = [
        'vendor_id_raw', 'hardware_raw', 'brand_raw', 'hz_advertised_friendly', 'hz_actual_friendly',
        'hz_advertised', 'hz_actual', 'arch', 'bits', 'count',
        'arch_string_raw', 'uname_string_raw',
        'l2_cache_size', 'l2_cache_line_size', 'l2_cache_associativity',
        'stepping', 'model', 'family',
        'processor_type', 'flags',
        'l3_cache_size', 'l1_data_cache_size', 'l1_instruction_cache_size'
    ]

    for key in keys:
        if new_info.get(key, None) and not info.get(key, None):
            info[key] = new_info[key]
        elif key == 'flags' and new_info.get('flags'):
            for f in new_info['flags']:
                if f not in info['flags']: info['flags'].append(f)
            info['flags'].sort()
            
def _get_cpu_info_internal():
    '''
    Returns the CPU info by using the best sources of information for your OS.
    Returns {} if nothing is found.
    '''

    # Get the CPU arch and bits
    arch, bits = _parse_arch(DataSource.arch_string_raw)

    friendly_maxsize = { 2**31-1: '32 bit', 2**63-1: '64 bit' }.get(sys.maxsize) or 'unknown bits'
    friendly_version = "{0}.{1}.{2}.{3}.{4}".format(*sys.version_info)
    PYTHON_VERSION = "{0} ({1})".format(friendly_version, friendly_maxsize)

    info = {
        'python_version' : PYTHON_VERSION,
        'arch' : arch,
        'bits' : bits,
        'count' : DataSource.cpu_count,
        'arch_string_raw' : DataSource.arch_string_raw,
    }

    # Try /proc/cpuinfo
    #_copy_new_fields(info, _get_cpu_info_from_proc_cpuinfo())

    # Try LSCPU
    #_copy_new_fields(info, _get_cpu_info_from_lscpu())
    return _get_cpu_info_from_lscpu()

def get_cpu_info():
    info = _get_cpu_info_internal()
    return info
