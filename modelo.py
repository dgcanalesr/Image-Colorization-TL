# -*- coding: utf-8 -*-

import tensorflow as tf
from layers import conv_layer
from layers import fc_layer
from layers import fusion_layer
from layers import output_layer


class modelo():
    
    #Inicializacion
    def __init__(self):
        self.inputs = tf.placeholder(shape=[config.BATCH_SIZE, config.IMAGE_SIZE, config.IMAGE_SIZE, 1], dtype=tf.float32)
        self.labels = tf.placeholder(shape=[config.BATCH_SIZE, config.IMAGE_SIZE, config.IMAGE_SIZE, 2], dtype=tf.float32)
        self.loss = None
        self.output = None
        
    #Capa convolucional
    def conv_layer(layer_name, tensor, shape, stride):
        weights = tf.get_variable("weights", shape, initializer = tf.contrib.layers.xavier_initializer_conv2d())
        biases = tf.get_variable("biases", [shape[3]], initializer=tf.constant_initializer(0.05))
        tf.summary.histogram(layer_name + "/weights", weights)
        tf.summary.histogram(layer_name + "/biases", biases)
        conv = tf.nn.conv2d(tensor, weights, stride, padding='SAME')
        return tf.nn.relu(conv + biases)
    
    #Capa fully-connected
    def fc_layer(layer_name, tensor, shape):
        weights = tf.get_variable("weights", shape, initializer = tf.contrib.layers.xavier_initializer())
        biases = tf.get_variable("biases", [shape[1]], initializer=tf.constant_initializer(0.0))
        tf.summary.histogram(layer_name + "/weights", weights)
        tf.summary.histogram(layer_name + "/biases", biases)
        mult_out = tf.matmul(tensor, weights)
        return tf.nn.relu(mult_out+biases)
    
    #Capa de fusion de features
    def fusion_layer(midlvl_features, global_features, shape, stride):
        midlvlft_shape = midlvl_features.get_shape().as_list()
        new_shape = [config.batch_size, midlvlft_shape[1]*midlvlft_shape[2], 256]
        midlvlft_reshaped = tf.reshape(midlvlft_shape, new_shape)
        fusion_lvl = []
        for j in range(midlvlft_reshaped[0]):
            for i in range(midlvlft_reshaped[1]):
                 see_mid = midlvlft_reshaped[j, i, :]
                 see_mid_shape = see_mid.get_shape().as_list()
                 see_mid = tf.reshape(see_mid, [1, see_mid_shape[0]])
                 global_features_shape = global_features[j, :].get_shape().as_list()
                 see_global = tf.reshape(global_features[j, :], [1, global_features_shape[0]])
                 fusion = tf.concat([see_mid, see_global], 1)
                 fusion_lvl.append(fusion)
        fusion_lvl = tf.stack(fusion_lvl, 1)
        fusion_shape = [config.batch_size, 28, 28, 512]
        fusion_lvl = tf.reshape(fusion_lvl, fusion_shape)
        return conv_layer('Fusion', fusion_lvl, shape, stride)
    
    #Capa de salida
    def output_layer(tensor, shape, stride):
        weights = tf.get_variable("weights", shape, initializer = tf.contrib.layers.xavier_initializer_conv2d())
        biases = tf.get_variable("biases", [shape[3]], initializer=tf.constant_initializer(0.05))
        conv = tf.nn.conv2d(tensor, weights, stride, padding='SAME')
        output_data = tf.nn.sigmoid(tf.nn.bias_add(conv, biases))
        return output_data
    
    #Construccion del modelo
    def build_model(self):
        input_data = self.inputs
        #capas para low-level features
        lowlvl = conv_layer('low_lvl_conv1', input_data, shape=[3, 3, 1, 64], stride=[1, 2, 2, 1])
        lowlvl = conv_layer('low_lvl_conv2', lowlvl, shape=[3, 3, 64, 128], stride=[1, 1, 1, 1])
        lowlvl = conv_layer('low_lvl_conv3', lowlvl, shape=[3, 3, 128, 128], stride=[1, 2, 2, 1])
        lowlvl = conv_layer('low_lvl_conv4', lowlvl, shape=[3, 3, 128, 256], stride=[1, 1, 1, 1])
        lowlvl = conv_layer('low_lvl_conv5', lowlvl, shape=[3, 3, 256, 256], stride=[1, 2, 2, 1])
        lowlvl = conv_layer('low_lvl_conv6', lowlvl, shape=[3, 3, 256, 512], stride=[1, 1, 1, 1])
        
        #capas para mid-level features
        midlvl = conv_layer('mid_lvl_conv1', lowlvl, shape=[3, 3, 512, 512], stride=[1, 1, 1, 1])
        midlvl = conv_layer('mid_lvl_conv2', midlvl, shape=[3, 3, 512, 256], stride=[1, 1, 1, 1])

        #capas conv para global features
        globalft = conv_layer('globalft_conv1', lowlvl, shape=[3, 3, 512, 512], stride=[1, 2, 2, 1])
        globalft = conv_layer('globalft_conv2', globalft, shape=[3, 3, 512, 512], stride=[1, 1, 1, 1])
        globalft = conv_layer('globalft_conv3', globalft, shape=[3, 3, 512, 512], stride=[1, 2, 2, 1])
        globalft = conv_layer('globalft_conv4', globalft, shape=[3, 3, 512, 512], stride=[1, 1, 1, 1])
        #capas fc para global features
        global_flat = tf.reshape(globalft, [config.BATCH_SIZE, -1])
        dim = global_flat.get_shape()[1].value
        globalft = fc_layer('global_fc1', global_flat, shape=[dim, 1024])
        globalft = fc_layer('global_fc2', globalft, shape=[1024, 512])
        globalft = fc_layer('global_fc3', globalft, shape=[512, 256])

        #capa de fusion
        ft = fusion_layer(midlvl, globalft, shape=[1, 1, 512, 256], stride=[1, 1, 1, 1])
        
        #capa de colorizacion
        ft = conv_layer('color_conv1', ft, shape=[3, 3, 256, 128], stride=[1, 1, 1, 1])
        ft = tf.image.resize_images(ft, [56, 56], method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
        ft = conv_layer('color_conv2', ft, shape=[3, 3, 128, 64], stride=[1, 1, 1, 1])
        ft = conv_layer('color_conv3', ft, shape=[3, 3, 64, 64], stride=[1, 1, 1, 1])
        ft = tf.image.resize_images(ft, [112, 112], method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
        ft = conv_layer('color_conv4', ft, shape=[3, 3, 64, 32], stride=[1, 1, 1, 1])

        #capa de salida 
        output = output_layer(ft, shape=[3, 3, 32, 2], stride=[1, 1, 1, 1])
        output = tf.image.resize_images(output, [224, 224], method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
        self.output = tf.image.resize_images(output, [224, 224], method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
        self.loss = tf.reduce_mean(tf.squared_difference(self.labels, self.output))





