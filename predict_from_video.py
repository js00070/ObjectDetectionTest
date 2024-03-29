import numpy as np
import os
import six.moves.urllib as urllib
import sys
import tarfile
import tensorflow as tf
import zipfile

from collections import defaultdict
from io import StringIO
from matplotlib import pyplot as plt
from PIL import Image
from IPython.display import display

from object_detection.utils import ops as utils_ops
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util

import ssr_interface

# patch tf1 into `utils.ops`
utils_ops.tf = tf.compat.v1

# Patch the location of gfile
tf.gfile = tf.io.gfile

def load_model(model_name):
  base_url = 'http://download.tensorflow.org/models/object_detection/'
  model_file = model_name + '.tar.gz'
  model_dir = tf.keras.utils.get_file(
    fname=model_name, 
    origin=base_url + model_file,
    untar=True)

  model_dir = pathlib.Path(model_dir)/"saved_model"

  model = tf.saved_model.load(str(model_dir))
  model = model.signatures['serving_default']

  return model

# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = 'data/mscoco_label_map.pbtxt'
category_index = label_map_util.create_category_index_from_labelmap(PATH_TO_LABELS, use_display_name=True)

import pathlib
PATH_TO_TEST_IMAGES_DIR = pathlib.Path('test_images')
TEST_IMAGE_PATHS = sorted(list(PATH_TO_TEST_IMAGES_DIR.glob("*.jpg")))

model_name = 'ssd_mobilenet_v1_coco_2017_11_17'
detection_model = load_model(model_name)

def run_inference_for_single_image(model, image):
  image = np.asarray(image)
  # The input needs to be a tensor, convert it using `tf.convert_to_tensor`.
  input_tensor = tf.convert_to_tensor(image)
  # The model expects a batch of images, so add an axis with `tf.newaxis`.
  input_tensor = input_tensor[tf.newaxis,...]

  # Run inference
  output_dict = model(input_tensor)

  # All outputs are batches tensors.
  # Convert to numpy arrays, and take index [0] to remove the batch dimension.
  # We're only interested in the first num_detections.
  num_detections = int(output_dict.pop('num_detections'))
  output_dict = {key:value[0, :num_detections].numpy() 
                 for key,value in output_dict.items()}
  output_dict['num_detections'] = num_detections

  # detection_classes should be ints.
  output_dict['detection_classes'] = output_dict['detection_classes'].astype(np.int64)
   
  # Handle models with masks:
  if 'detection_masks' in output_dict:
    # Reframe the the bbox mask to the image size.
    detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
              output_dict['detection_masks'], output_dict['detection_boxes'],
               image.shape[0], image.shape[1])      
    detection_masks_reframed = tf.cast(detection_masks_reframed > 0.5,
                                       tf.uint8)
    output_dict['detection_masks_reframed'] = detection_masks_reframed.numpy()
    
  return output_dict

def show_inference(model, image_path):
  # the array based representation of the image will be used later in order to prepare the
  # result image with boxes and labels on it.
  image_np = np.array(Image.open(image_path))
  print(image_np.shape)
  # Actual detection.
  output_dict = run_inference_for_single_image(model, image_np)
  # print(output_dict['detection_scores'])
  res = []
  for i in range(len(output_dict['detection_classes'])):
    if output_dict['detection_scores'][i] >= 0.50:
      print("class {}, score {}, box {}".format(output_dict['detection_classes'][i], output_dict['detection_scores'][i], output_dict['detection_boxes'][i]))
      if output_dict['detection_classes'][i]==1:
        res.append(output_dict['detection_boxes'][i])
  print("==================")
  # Visualization of the results of a detection.
#   vis_util.visualize_boxes_and_labels_on_image_array(
#       image_np,
#       output_dict['detection_boxes'],
#       output_dict['detection_classes'],
#       output_dict['detection_scores'],
#       category_index,
#       instance_masks=output_dict.get('detection_masks_reframed', None),
#       use_normalized_coordinates=True,
#       line_thickness=8)

#   display(Image.fromarray(image_np))

for image_path in TEST_IMAGE_PATHS:
  show_inference(detection_model, image_path)

import cv2

video_src = '1.mp4'

#　cap = cv2.VideoCapture(video_src) # 从视频文件读取

cap = cv2.VideoCapture(0) # 从usb摄像头读取

personExist = False

while True:
  ret, img = cap.read()
  if (type(img) == type(None)):
    break
  image_np = np.array(img)
  height, width, depth = img.shape
  output_dict = run_inference_for_single_image(detection_model, image_np)
  res = []
  for i in range(len(output_dict['detection_classes'])):
    if output_dict['detection_scores'][i] >= 0.70: # 阈值可以调整
      if output_dict['detection_classes'][i]==1:
        res.append(output_dict['detection_boxes'][i])

  if len(res)>0:
    a,b,c,d = res[0] # a是左上角的点距离顶边的距离，b是左上角的点距离左侧边的距离，cd分别是右下角的点距离顶边与左侧边的距离
    print("a,b,c,d = {},{},{},{}".format(a,b,c,d))

    # 具体的坐标计算方法需要实地测量，这里只是先随便赋一下值
    X = (b+d)/2 - 0.5
    Y = 1 # Y值需要测距然后用相似三角形来算。。。
    Z = 0 # Z值也一样

    if not personExist:
      ssr_interface.NewSource({
        "id": "person",
        "name": "person",
        "port-number": 1,
        "pos": [X,Y,Z],
        "volume": 0.1
      })
      personExist = True
    else:
      ssr_interface.ModSource("person",{
        "pos": [X,Y,Z]
      })
  else:
    if personExist:
      ssr_interface.DeleteSource("person")
      personExist = False

  for (a,b,c,d) in res:
    cv2.rectangle(img,(int(b*width),int(a*height)),(int(d*width),int(c*height)),(0,255,210),4)

  cv2.imshow('video', img)
  if cv2.waitKey(33) == 27:
    break

cv2.destroyAllWindows()