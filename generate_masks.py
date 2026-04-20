""" Read gates from a csv file, and use them to generate and write masks in the appropriate mask directory.
    This is the script to run to label gates, as the csv file will initially only contain the names of the files.
"""

import cv2
import numpy as np
import os
import copy
import csv
import yaml
from yaml.loader import SafeLoader
from rich.progress import track


#############################################
## Loading and saving corners files
#############################################

def parse_csv_gate(gate_corners, n_vars_per_gate = 8):
    
    """ Parse gate corners from a csv entry. """
        
    gate = []
    if len(gate_corners) != n_vars_per_gate:
        # Error
        return gate_corners

    for i in range(0,n_vars_per_gate,2):
        x = int(round(float(gate_corners[i])))
        y = int(round(float(gate_corners[i+1])))
        gate.append((x,y))
    return gate



""" Functions to calculate corner distance, central gate coordinate and average distance, finding the closest corner to a point.
"""


def corner_distance(point, corner):
    dx = point[0] - corner[0]
    dy = point[1] - corner[1]
    return np.sqrt(dx*dx+dy*dy)
    

def gate_smallest_edge(gate):

    """ Find the shortest edge of a gate. """

    smallest = 1000000
    for i in range(0,4):
        ii = i-1
        if ii < 0:
            ii = 3
        s = corner_distance(gate[i],gate[ii])
        if s < smallest:
            smallest = s
    return smallest


def read_csv(filename='./corners.csv'):
    
    d = dict([])
    if not os.path.exists(filename):
        return d

    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            # get the gate corners from the current row
            gate = parse_csv_gate(row[1:])
            # if the image has already a gate associate it, append this gate
            # else, make a new entry in the dictionary with the image name
            if(row[0] in d):
                d[row[0]].append(gate)
            else:
                if gate == []: # image with no gates
                    d.update({row[0]:[]})
                else:
                    d.update({row[0]:[gate]})
    return d



#############################################
## Drawing gates with perspective transform
#############################################


DEFAULT_OFFSET_SCALAR = 0.09; # only this variable is really used, it represents the border width as a ratio of the full gate size.


def get_perspective(corners, image_shape, offset_scalar=DEFAULT_OFFSET_SCALAR, camera_calibration=None):
    
    """ Based on the inner corners, calculate the outer corner coordinates.
        - offset_gate is ...
    """

    offset_gate_x = int(image_shape[0]*1.5)
    offset_gate_y = int(image_shape[1]*0.5)
    mask=np.zeros((image_shape[0]*3,image_shape[1]*3),np.uint8)


    # corners in the image
    rect = np.array([
        [corners[0][0], corners[0][1]],
        [corners[1][0], corners[1][1]],
        [corners[2][0], corners[2][1]],
        [corners[3][0], corners[3][1]]], dtype="float32")
    (tl, tr, br, bl) = rect

    # identify the longest side:
    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))
    max_height = max(int(height_a), int(height_b))
    max_length = max(max_width, max_height)

    # corners in the image if we would look straight at the gate:
    dst = np.array([
        [corners[0][0] + offset_gate_x, corners[0][1] + offset_gate_y],
        [corners[0][0] + offset_gate_x + max_length - 1, corners[0][1] + offset_gate_y],
        [corners[0][0] + offset_gate_x + max_length - 1, corners[0][1] + offset_gate_y + max_length - 1],
        [corners[0][0] + offset_gate_x, corners[0][1] + offset_gate_y + max_length - 1]], dtype=np.float32)

    # get the projective transform to go from the current coordinates to the straight ones
    M = cv2.getPerspectiveTransform(rect, dst)
    # and back:
    Minv = cv2.invert(M)[-1]

    # calculate the offset in pixels for the border, defined as a ratio of the total gate size:
    off = max_length * offset_scalar
    offset = [[(-2.*off,-2.*off), (2.*off, 0)], 
        [(0, -2.*off), (2.*off, 2.*off)],
        [(2.*off, 0), (-2.*off, 2.*off)],
        [(0, 2.*off), (-2.*off, -2.*off)]]

    # construct the border as four rectangles:
    for i in range(0,dst.shape[0]):
        end = i+1
        if i == len(corners)-1: end = 0
        xs = np.clip([int(dst[i,0] + offset[i][0][0]), int(dst[end,0] + offset[i][1][0])], 0, mask.shape[1])
        ys = np.clip([int(dst[i,1] + offset[i][0][1]), int(dst[end,1] + offset[i][1][1])], 0, mask.shape[0])
        cv2.rectangle(mask, (xs[0], ys[0]), (xs[1], ys[1]), (255,255,255), -1)

    return cv2.warpPerspective(mask, Minv, dsize=(mask.shape[1], mask.shape[0]))[0:image_shape[0], 0:image_shape[1]]



def gate_bouding_circle(gate):
    
    """ Calculate the center coordinate of a gate, and the average distance of the corners to that center. """
    
    # Center point is the average
    x = 0
    y = 0
    for g in gate:
        x = x + g[0]
        y = y + g[1]
    c = (int(x/4), int(y/4))

    # Compute the average distance from corners to the center
    d = 0
    for g in gate:
        d = d + corner_distance(c, g)
    d = d / 4.0
    
    return (c, int(d))


def draw_gates_in_image(img_p, gate_list, gate_border_size, camera_calibration, show_corners=True):

    """ Takes the RGB image and gate list, generates and returns the mask, and potentially shows the image with the mask in the red channel.
    """

    mask = np.zeros((2*img_p.shape[0],2*img_p.shape[1]), np.uint8)
    mask_final = np.zeros((img_p.shape[0],img_p.shape[1]), np.uint8)
    mask_rejected = np.zeros((img_p.shape[0],img_p.shape[1]), np.uint8)
    offset_gate = int(img_p.shape[0] / 2)

    for gate in gate_list:

        # Compute some metrics
        box = gate_bouding_circle(gate)
        short = gate_smallest_edge(gate)

        """ - Learning will resize the image by half, if it was larger than 720
            - Then it will crop a randon 360 * 360 px box
            - So all thresholds are relative to 360, or 360 after resizing / 2, which is 720 in the original 
        """

        scale = 360.0
        if img_p.shape[0] >= 720:
            scale = 720.0

        h = 2 * box[1] / float(scale)
        s = short / float(scale)
        good = 1

        # Compute Gate Perspective from inner corners
        mask = get_perspective(gate, img_p.shape, gate_border_size, camera_calibration)

        # Only add to mask if large
        if (good == 1):
            mask_final[mask > 0] = 255

        # Draw all good and all bad for labeling
        mask_rejected[mask > 0] = 255
        img_p[:,:,2] = mask_rejected[:,:]

    return mask_final



#############################################
## Dataset settings
#############################################


def load_dataset_info( dataset_yaml_file, verbose=False ):

    if not os.path.exists(dataset_yaml_file):
        if verbose:
            print("Creating", dataset_yaml_file)
        with open(dataset_yaml_file, 'w') as f:
            f.write('location: Unknown\n')

    with open(dataset_yaml_file) as f:
        yamlfile = yaml.load(f, Loader=SafeLoader)

    missing = False

    # Check all elements are present, or add them

    elements = ['location', 'gate_type', 'gate_border_size']

    for element in elements:
        if yamlfile == None:
            yamlfile = dict([])
        if not yamlfile.__contains__(element):
            # add it to the dictionary
            yamlfile[element] = 'Unknown'
            missing = True
    
    # Check all values that need to be numbers
    try:
        gb = float(yamlfile['gate_border_size'])
    except:
        print('DATASET WARNING: gate_border_size is not a number')
        yamlfile['gate_border_size'] = 0.19
        missing = True


    if missing:
        with open(dataset_yaml_file, 'w') as f:
            yaml.dump(yamlfile, f, default_flow_style=False)

    return yamlfile




#############################################
## Main
#############################################


if __name__ == "__main__":
    main_folder = './data/'

    dataset_folders = [ 'adnec_s1_f1/', 'dhl_s1_f1/', 'marina_s1_f1/', 'red_s1_f1/', 'red_s1_f2/', 'red_s1_f3/' ]

    global gate_list

    for ds in dataset_folders:
        #print(ds)

        info = os.path.join(main_folder, ds, 'data.yaml')
        info = load_dataset_info(info)

        gate_border_size = float(info['gate_border_size'])
        camera_calibration = None

        images = read_csv(os.path.join(main_folder, ds, 'corners.csv'))
        
        if (len(images)):
            # print first row of csv
            num_cols =len(images[list(images.keys())[0]][0])

            is_manual_dataset = (num_cols == 16)

            if not is_manual_dataset:
                for i in track(images, description=f"Generate {ds} masks type ."):
                    fname = main_folder + ds + i

                    if not os.path.isfile(fname):
                        print('ERROR: ', fname, ' does not exist')
                        break

                    img = cv2.imread(fname)
                    gate_list = images[i]

                    img_show = copy.deepcopy(img)
                    mask_final = draw_gates_in_image(img_show, gate_list, gate_border_size, camera_calibration, show_corners=False)

                    save_file = fname.replace('img_', 'mask_', 1)

                    cv2.imwrite(save_file, mask_final)

                    save_file = fname.replace('img_', 'check_', 1)

                    # Check if image and mask have the same size
                    if img.shape[:2] != mask_final.shape[:2]:
                        # Resize the image to the mask size
                        img = cv.resize(img, (mask_final.shape[1], mask_final.shape[0]))

                    img[:,:,2] = mask_final[:,:]
                    cv2.imwrite(save_file, img)

