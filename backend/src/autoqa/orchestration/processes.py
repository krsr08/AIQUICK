"""Bounded process trees: Windows Job Objects / POSIX process groups."""
import ctypes
import os
import signal
import subprocess
import time

class WorkerCancelled(Exception):
    """Raised only after the worker's process-tree cleanup has completed."""

def bounded_worker(command, *, payload, environment, timeout, cancelled=None):
    if cancelled is not None and cancelled():
        raise WorkerCancelled()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, env=environment, start_new_session=os.name != 'nt')
    job = None
    kernel = None
    try:
        if os.name == 'nt':
            from ctypes import wintypes
            class Basic(ctypes.Structure):
                _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                    ('flags', wintypes.DWORD), ('min_working', ctypes.c_size_t), ('max_working', ctypes.c_size_t),
                    ('active_limit', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                    ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
            class IO(ctypes.Structure):
                _fields_ = [(name, ctypes.c_uint64) for name in ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]
            class Extended(ctypes.Structure):
                _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                    ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CreateJobObjectW.restype = wintypes.HANDLE
            kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
            kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
            kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
            kernel.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
            job = kernel.CreateJobObjectW(None, None)
            limits = Extended()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                raise OSError('Cannot establish worker job containment')
            if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(process._handle)):
                raise OSError('Cannot assign worker to job')
        # Worker reads stdin before creating any descendants; containment is now active.
        deadline = time.monotonic() + timeout
        first = True
        while True:
            if cancelled is not None and cancelled():
                raise WorkerCancelled()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                output, _ = process.communicate(payload if first else None, timeout=min(.25, remaining))
                break
            except subprocess.TimeoutExpired:
                first = False
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
        return output
    finally:
        cleanup_error = None
        if job:
            try:
                class Accounting(ctypes.Structure):
                    _fields_ = [('total_user', ctypes.c_int64), ('total_kernel', ctypes.c_int64),
                        ('period_user', ctypes.c_int64), ('period_kernel', ctypes.c_int64),
                        ('faults', wintypes.DWORD), ('total', wintypes.DWORD),
                        ('active', wintypes.DWORD), ('terminated', wintypes.DWORD)]
                if not kernel.TerminateJobObject(job, 1):
                    raise OSError('Worker process-tree termination failed')
                stop_deadline = time.monotonic() + 10
                while True:
                    accounting = Accounting()
                    if not kernel.QueryInformationJobObject(job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None):
                        raise OSError('Worker process-tree shutdown could not be verified')
                    if accounting.active == 0:
                        break
                    if time.monotonic() >= stop_deadline:
                        raise OSError('Worker process-tree shutdown deadline exceeded')
                    time.sleep(.02)
            except OSError as error:
                cleanup_error = error
            finally:
                if not kernel.CloseHandle(job):
                    cleanup_error = OSError('Worker process-tree handle cleanup failed')
        elif os.name != 'nt':
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        if os.name != 'nt':
            stop_deadline = time.monotonic() + 10
            while True:
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    break
                if time.monotonic() >= stop_deadline:
                    cleanup_error = OSError('Worker process-group shutdown could not be verified')
                    break
                time.sleep(.02)
        if cleanup_error is not None:
            raise cleanup_error
