#define PY_SSIZE_T_CLEAN  /* Make "s#" use Py_ssize_t rather than int. */
#include <Python.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static PyObject *
xpcu_calc_xfer_payload(PyObject *self, PyObject *args){
  int count;
  PyObject *itmsbytes;
  PyObject *itdibytes;
  PyObject *itdobytes;

  //Arguments: int, byteiter, byteiter, byteiter
  if (!PyArg_ParseTuple(args, "IOOO", &count, &itmsbytes,
			&itdibytes, &itdobytes))
    return NULL;
  assert(PyIter_Check(itmsbytes));
  assert(PyIter_Check(itdibytes));
  assert(PyIter_Check(itdobytes));

  PyObject* res =
    PyBytes_FromStringAndSize(NULL, (int)(ceil(count/4.0)*2));
  if (!res)
    return NULL;

  char* buff = PyBytes_AsString(res);

  Py_ssize_t off = 2*((count%8-4>-1)+(count%4>0));
  PyObject *_otms, *_otdi, *_otdo;
  uint8_t _tms, _tdi, _tdo;
  for (int i = count/8 - 1; i >= 0; i--){
    _otms = PyIter_Next(itmsbytes);
    _otdi = PyIter_Next(itdibytes);
    _otdo = PyIter_Next(itdobytes);
    _tms = PyNumber_AsSsize_t(_otms, NULL);
    _tdi = PyNumber_AsSsize_t(_otdi, NULL);
    _tdo = PyNumber_AsSsize_t(_otdo, NULL);
    Py_DECREF(_otms);
    Py_DECREF(_otdi);
    Py_DECREF(_otdo);

    buff[off+(i<<2)+2] = (_tms&0xF0)|(_tdi>>4);
    buff[off+(i<<2)+3] = (_tdo&0xF0)|0x0F;
    buff[off+(i<<2)] = ((_tms<<4)&0xF0)|(_tdi&0x0F);
    buff[off+(i<<2)+1] = ((_tdo<<4)&0xF0)|0x0F;
  }

  if (count%8){
    _otms = PyIter_Next(itmsbytes);
    _otdi = PyIter_Next(itdibytes);
    _otdo = PyIter_Next(itdobytes);
    _tms = PyNumber_AsSsize_t(_otms, NULL);
    _tdi = PyNumber_AsSsize_t(_otdi, NULL);
    _tdo = PyNumber_AsSsize_t(_otdo, NULL);
    Py_DECREF(_otms);
    Py_DECREF(_otdi);
    Py_DECREF(_otdo);
  }
  if (count%8-4>-1){
    //0xAa 0xBb 0xCc 0xDd = 0xab 0xcd
    buff[(count%4>0)<<1] = (_tms&0xF0)|(_tdi>>4);
    buff[((count%4>0)<<1)+1] = (_tdo&0xF0)|0x0F;
    if (count%4){
      //0xAa 0xBb 0xCc 0xDd = 0xAB 0xCD
      buff[0] = ((_tms&0x0F)<<4)|(_tdi&0x0F);
      buff[1] = ((_tdo&0x0F)<<4)|(0xF-((1<<(4-(count%4)))-1));
    }
  }else if (count%4){
    //0xAa 0xBb 0xCc 0xDd = 0xAB 0xCD
    buff[0]= (_tms&0xF0)|(_tdi>>4);
    buff[1] = (_tdo&0xF0)|(0xF-((1<<(4-(count%4)))-1));
  }

  return res;
}

static PyMethodDef XpcuMethods[] = {
      {"calc_xfer_payload",  xpcu_calc_xfer_payload, METH_VARARGS,
       "Calculates a bytestream from 3 byte iters to send to the XPCU1."},
      {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef xpcumodule = {
  PyModuleDef_HEAD_INIT,
  "_xpcu1utils",/* name of module */
  NULL,         /* module documentation */
  -1,           /* size of per-interpreter state of the module,
		   or -1 if the module keeps state in global variables.*/
  XpcuMethods
};

PyMODINIT_FUNC
PyInit__xpcu1utils(void)
{
  return PyModule_Create(&xpcumodule);
}
