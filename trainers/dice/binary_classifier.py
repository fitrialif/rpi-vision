# python
import os
from datetime import datetime
import argparse
import tarfile
import urllib

# lib
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D
from keras.layers import Activation, Dropout, Flatten, Dense
from keras import backend as K
from google.cloud import storage
import trainers
from trainers.common import TimeHistory

# inspired by https://gist.github.com/fchollet/0830affa1f7f19fd47b06d4cf89ed44d

# replace with path to your bucket!
BATCH_SIZE = 16

IMG_HEIGHT, IMG_WIDTH = 480, 480


NUM_TRAIN_SAMPLES = 14290
NUM_VALIDATION_SAMPLES = 210

if K.image_data_format() == "channels_first":
    input_shape = (3, IMG_WIDTH, IMG_HEIGHT)
else:
    input_shape = (IMG_WIDTH, IMG_HEIGHT, 3)


def main():

    REMOTE_DATA_PATH = (
        "https://storage.googleapis.com/raspberry-pi-vision/dice/data.tar.gz"
    )

    MODULE_PATH = os.path.dirname(os.path.realpath(__file__))
    LOCAL_DATA_PATH = MODULE_PATH + "/data/"

    # only download and extract tar'd data if raspberry-pi-vision/trainers/dice/data/ does not exist
    if not os.path.isdir(LOCAL_DATA_PATH):
        file_path = MODULE_PATH + "/data.tar.gz"
        if not os.path.isfile(file_path):
            print("Downloading {0}".format(REMOTE_DATA_PATH))
            file = urllib.request.URLopener()
            file.retrieve(REMOTE_DATA_PATH, file_path)
        print("Extracting {0}".format(file_path))
        tar = tarfile.open(file_path)
        tar.extractall(MODULE_PATH)
        tar.close()

    model = Sequential()
    model.add(Conv2D(32, (3, 3), input_shape=input_shape))
    model.add(Activation("relu"))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(32, (3, 3)))
    model.add(Activation("relu"))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(64, (3, 3)))
    model.add(Activation("relu"))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Flatten())
    model.add(Dense(64))
    model.add(Activation("relu"))
    model.add(Dropout(0.5))
    model.add(Dense(1))
    model.add(Activation("sigmoid"))

    model.compile(loss="binary_crossentropy", optimizer="rmsprop", metrics=["accuracy"])

    train_datagen = ImageDataGenerator(
        rotation_range=40,
        width_shift_range=0.2,
        height_shift_range=0.2,
        rescale=1.0 / 255,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True,
        fill_mode="nearest",
    )

    test_datagen = ImageDataGenerator(rescale=1.0 / 255)

    train_generator = train_datagen.flow_from_directory(
        LOCAL_DATA_PATH + "train/",
        target_size=(IMG_WIDTH, IMG_HEIGHT),
        batch_size=BATCH_SIZE,
        class_mode="binary",
    )

    validation_generator = test_datagen.flow_from_directory(
        LOCAL_DATA_PATH + "valid/",
        target_size=(IMG_WIDTH, IMG_HEIGHT),
        batch_size=BATCH_SIZE,
        class_mode="binary",
    )

    time_callback = TimeHistory()

    model.fit_generator(
        train_generator,
        steps_per_epoch=NUM_TRAIN_SAMPLES // BATCH_SIZE,
        epochs=50,
        validation_data=validation_generator,
        validation_steps=NUM_VALIDATION_SAMPLES // BATCH_SIZE,
        callbacks=[time_callback],
    )

    model.save_weights(LOCAL_DATA_PATH + "weights_" + trainers.__version__ + ".h5")
    model.save(LOCAL_DATA_PATH + "model_" + trainers.__version__ + ".h5")

    storage_client = storage.Client()
    bucket = storage_client.get_bucket("raspberry-pi-vision")
    w_blob = bucket.blob(
        "dice/models/weights_{0}_{1}".format(trainers.__version__, datetime.utcnow())
    )
    w_blob.upload_from_filename(
        filename=LOCAL_DATA_PATH + "weights_" + trainers.__version__ + ".h5"
    )

    m_blob = bucket.blob(
        "dice/models/model_{0}_{1}".format(trainers.__version__, datetime.utcnow())
    )
    m_blob.upload_from_filename(
        filename=LOCAL_DATA_PATH + "model_" + trainers.__version__ + ".h5"
    )


if __name__ == "__main__":
    main()

