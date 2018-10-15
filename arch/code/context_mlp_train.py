import os
CPU = True
if CPU:
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"   # see issue https://stackoverflow.com/questions/40690598/can-keras-with-tensorflow-backend-be-forced-to-use-cpu-or-gpu-at-will
    os.environ["CUDA_VISIBLE_DEVICES"] = ""  # This must be imported before keras

from keras.utils import to_categorical
from keras.callbacks import ModelCheckpoint

from context_mlp_model import context_create_model, compile_model
from context_data import load_split, get_AVA_set, get_AVA_labels

import pickle
import utils


def main():
    K.clear_session()

    # Load list of action classes and separate them (from utils_stream)
    classes = utils.get_AVA_classes('ava_action_list_custom.csv')

    # Parameters for training (batch size 32 is supposed to be the best?)
    context_dim = 630
    params = {'dim': context_dim, 'batch_size': 64, 'n_classes': len(classes['label_id']), 'n_channels': 1, 'nb_epochs': 200, 'model': "mlp"}

    root_dir = '../../data/AVA/files/'

    # Get ID's and labels from the actual dataset
    partition = {}
    partition['train'] = get_AVA_set(classes=classes, filename=root_dir + "AVA_Train_Custom_Corrected.csv")  # IDs for training
    partition['validation'] = get_AVA_set(classes=classes, filename=root_dir + "AVA_Validation_Custom_Corrected.csv")  # IDs for validation

    # Labels
    labels_train = get_AVA_labels(classes, partition, "train", filename=root_dir + "AVA_Train_Custom_Corrected.csv")
    labels_val = get_AVA_labels(classes, partition, "validation", filename=root_dir + "AVA_Validation_Custom_Corrected.csv")
    # pprint.pprint(labels_val)

    # Create + compile model, load saved weights if they exist
    NHU1V = [32, 64, 128, 256, 512]
    NHU2V = [16, 32, 64, 128, 256]
    for NHU1, NHU2 in zip(NHU1V, NHU2V):
        bestModelPath = "context_mlp" + str(NHU1) + ".hdf5"
        histPath = "contextHistory_" + str(NHU1)
        checkpointer = ModelCheckpoint(filepath=bestModelPath, monitor='val_loss', verbose=1, save_best_only=True, save_weights_only=False, period=1)
        model = context_create_model(NHU1, NHU2, in_shape=(params['dim'],))
        model = compile_model(model)

        x_val = y_val_pose = y_val_object = y_val_human = x_train = y_train_pose = y_train_object = y_train_human = None

        # Load train data
        Xfilename = root_dir + "context_files/XContext_train_tw3.csv"
        x_train, y_train_pose, y_train_object, y_train_human = load_split(partition['train'], labels_train, params['dim'], params['n_channels'], "train", Xfilename)
        y_t = []
        y_t.append(to_categorical(y_train_pose, num_classes=utils.POSE_CLASSES))
        y_t.append(utils.to_binary_vector(y_train_object, size=utils.OBJ_HUMAN_CLASSES, labeltype='object-human'))
        y_t.append(utils.to_binary_vector(y_train_human, size=utils.HUMAN_HUMAN_CLASSES, labeltype='human-human'))

        # Load val data
        Xfilename = root_dir + "contextData/XContext_val_tw3.csv"
        x_val, y_val_pose, y_val_object, y_val_human = load_split(partition['validation'], labels_val, params['dim'], params['n_channels'], Xfilename)
        y_v = []
        y_v.append(to_categorical(y_val_pose, num_classes=utils.POSE_CLASSES))
        y_v.append(utils.to_binary_vector(y_val_object, size=utils.OBJ_HUMAN_CLASSES, labeltype='object-human'))
        y_v.append(utils.to_binary_vector(y_val_human, size=utils.HUMAN_HUMAN_CLASSES, labeltype='human-human'))

        # Train
        hist = model.fit(x_train, y_t, batch_size=params['batch_size'], validation_data=(x_val, y_v), epochs=params['nb_epochs'], verbose=1, callbacks=[checkpointer])

        # model.save(bestModelPath)
        with open(histPath, 'wb') as file_pi:
            pickle.dump(hist.history, file_pi)


if __name__ == '__main__':
    main()