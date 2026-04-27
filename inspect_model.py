"""
Inspect model.h5 to identify architecture and final layer.
This script first tries to load with Keras. If TensorFlow/Keras isn't available
or the model fails to load, it falls back to inspecting the HDF5 structure
with h5py and searches for layer name hints (e.g., 'mobilenet', 'resnet').
"""

import sys
import traceback

MODEL_PATH = 'model.h5'

def try_load_with_keras():
    try:
        from tensorflow.keras.models import load_model
        print('Attempting to load model with tensorflow.keras...')
        model = load_model(MODEL_PATH)
        print('\nModel loaded successfully with Keras/TensorFlow.\n')
        print('--- Model summary ---')
        model.summary()
        print('\n--- Last layer info ---')
        last = model.layers[-1]
        print('Last layer class:', last.__class__.__name__)
        try:
            cfg = last.get_config()
            print('Last layer config keys:', list(cfg.keys()))
        except Exception as e:
            print('Could not read last layer config:', e)
        # search layer names for common backbone hints
        layer_names = [l.name.lower() for l in model.layers]
        hints = set()
        for name in layer_names:
            for keyword in ('mobilenet', 'resnet', 'vgg', 'inception', 'efficientnet', 'conv_pw', 'dw_conv'):
                if keyword in name:
                    hints.add(keyword)
        if hints:
            print('\nDetected backbone hints in layer names:', hints)
        else:
            print('\nNo obvious backbone keywords found in the first/last layer names sample.')
        return True
    except Exception as e:
        print('Keras load failed:', e)
        traceback.print_exc()
        return False


def inspect_hdf5():
    try:
        import h5py
        print('\nFalling back to HDF5 inspection using h5py...')
        with h5py.File(MODEL_PATH, 'r') as f:
            print('Top-level keys:', list(f.keys()))
            # check for layer names attribute
            if 'layer_names' in f:
                try:
                    layer_names = [n.decode('utf-8') if isinstance(n, bytes) else n for n in f['layer_names']]
                    print('\nlayer_names (first 20):')
                    for n in layer_names[:20]:
                        print(' -', n)
                except Exception:
                    print('Could not decode layer_names attribute directly')
            # Check for model config
            if 'model_config' in f:
                try:
                    mc = f['model_config'][()]
                    print('\nFound model_config (truncated):')
                    print(str(mc)[:1000])
                except Exception:
                    print('Could not read model_config content')
            # search for strings mentioning common backbones
            found = set()
            def visit(name, obj):
                try:
                    if isinstance(obj, h5py.Dataset):
                        val = None
                        try:
                            # read small slice or decode if bytes
                            val = obj[()]
                        except Exception:
                            pass
                        if isinstance(val, (bytes, str)):
                            s = val.decode('utf-8') if isinstance(val, bytes) else val
                            for kw in ('mobilenet', 'resnet', 'vgg', 'inception', 'efficientnet'):
                                if kw in s.lower():
                                    found.add(kw)
                except Exception:
                    pass
            f.visititems(visit)
            if found:
                print('\nBackbone hints found inside HDF5 datasets:', found)
            else:
                print('\nNo backbone keywords found in HDF5 content scan.')
    except Exception as e:
        print('HDF5 inspection failed:', e)
        traceback.print_exc()


if __name__ == '__main__':
    print('Inspecting', MODEL_PATH)
    ok = try_load_with_keras()
    if not ok:
        inspect_hdf5()
    print('\nInspection finished.')
