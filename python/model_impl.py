import cPickle as pkl

import numpy as np
import tensorflow as tf
import xgboost as xgb
from sklearn.metrics import log_loss

import utils
from model import *


class GBLinear(Classifier):
    def __init__(self, name, eval_metric, input_spaces, num_class,
                 num_round=10, early_stop_round=None, verbose=True,
                 gblinear_alpha=0, gblinear_lambda=0, random_state=0):
        Classifier.__init__(self, name, eval_metric, input_spaces, num_class)
        self.params = {
            'booster': 'gblinear',
            'silent': 1,
            'num_class': num_class,
            'lambda': gblinear_lambda,
            'alpha': gblinear_alpha,
            'objective': 'multi:softprob',
            'seed': random_state,
            'eval_metric': 'mlogloss',
        }
        self.bst = None
        self.num_round = num_round
        self.early_stop_round = early_stop_round
        self.verbose = verbose

    def train(self, dtrain, dvalid=None):
        if dvalid is not None:
            watchlist = [(dtrain, 'train'), (dvalid, 'eval')]
            self.bst = xgb.train(self.params, dtrain,
                                 num_boost_round=self.num_round,
                                 early_stopping_rounds=self.early_stop_round,
                                 evals=watchlist,
                                 verbose_eval=self.verbose)
            train_score = log_loss(dtrain.get_label(), self.predict(dtrain))
            valid_score = log_loss(dvalid.get_label(), self.predict(dvalid))
            print '[-1]\ttrain: %f\tvalid: %f' % (train_score, valid_score)
            return train_score, valid_score
        else:
            watchlist = [(dtrain, 'train')]
            self.bst = xgb.train(self.params, dtrain,
                                 num_boost_round=self.num_round,
                                 evals=watchlist,
                                 verbose_eval=self.verbose)
            train_pred = self.predict(dtrain)
            train_score = log_loss(dtrain.get_label(), train_pred)
            print '[-1]\ttrain: %f' % train_score
            return train_score

    def predict(self, data):
        return self.bst.predict(data)

    def dump(self):
        self.bst.save_model(self.get_bin_path())
        self.bst.dump_model(self.get_file_path())
        print 'model dumped at', self.get_bin_path(), self.get_file_path()


class GBTree(Classifier):
    def __init__(self, name, eval_metric, input_spaces, num_class, num_round=10, early_stop_round=None, verbose=True,
                 eta=0.1, max_depth=3, subsample=0.7, colsample_bytree=0.7, gbtree_alpha=0, gbtree_lambda=0,
                 random_state=0):
        Classifier.__init__(self, name, eval_metric, input_spaces, num_class)
        self.params = {
            "booster": 'gbtree',
            "silent": 1,
            "num_class": num_class,
            "eta": eta,
            "max_depth": max_depth,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "lambda": gbtree_lambda,
            "alpha": gbtree_alpha,
            "objective": "multi:softprob",
            "seed": random_state,
            "eval_metric": "mlogloss",
        }
        self.bst = None
        self.num_round = num_round
        self.early_stop_round = early_stop_round
        self.verbose = verbose

    def train(self, dtrain, dvalid=None):
        if dvalid is not None:
            watchlist = [(dtrain, 'train'), (dvalid, 'eval')]
            self.bst = xgb.train(self.params, dtrain,
                                 num_boost_round=self.num_round,
                                 early_stopping_rounds=self.early_stop_round,
                                 evals=watchlist,
                                 verbose_eval=self.verbose)
            train_score = log_loss(dtrain.get_label(), self.predict(dtrain))
            valid_score = log_loss(dvalid.get_label(), self.predict(dvalid))
            print '[-1]\ttrain: %f\tvalid: %f' % (train_score, valid_score)
            return train_score, valid_score
        else:
            watchlist = [(dtrain, 'train')]
            self.bst = xgb.train(self.params, dtrain,
                                 num_boost_round=self.num_round,
                                 evals=watchlist,
                                 verbose_eval=self.verbose)
            train_pred = self.predict(dtrain)
            train_score = log_loss(dtrain.get_label(), train_pred)
            print '[-1]\ttrain: %f' % train_score
            return train_score

    def predict(self, data):
        return self.bst.predict(data, ntree_limit=self.bst.best_iteration)

    def dump(self):
        self.bst.save_model(self.get_bin_path())
        self.bst.dump_model(self.get_file_path())
        print 'model dumped at', self.get_bin_path(), self.get_file_path()


class TFClassifier(Classifier):
    def __init__(self, name, eval_metric, input_spaces, num_class,
                 batch_size=None, num_round=None, early_stop_round=None, verbose=True, save_log=True):
        Classifier.__init__(self, name, eval_metric, input_spaces, num_class)
        self.__graph = None
        self.__sess = None
        self.x = None
        self.y_true = None
        self.drops = None
        self.vars = None
        self.y = None
        self.y_prob = None
        self.loss = None
        self.optimizer = None
        self.init_path = None
        self.init_actions = None
        self.layer_drops = None
        self.batch_size = batch_size
        self.num_round = num_round
        self.early_stop_round = early_stop_round
        self.verbose = verbose
        self.save_log = save_log

    def __del__(self):
        self.__sess.close()

    def build_graph(self):
        pass

    def run(self, fetches, feed_dict=None):
        return self.__sess.run(fetches, feed_dict)

    def compile(self):
        self.__graph = tf.Graph()
        with self.__graph.as_default():
            if utils.check_type(self.get_input_spaces(), 'int'):
                self.x = tf.sparse_placeholder(tf.float32)
            else:
                self.x = map(lambda x: tf.sparse_placeholder(tf.float32), self.get_input_spaces())
            self.y_true = tf.placeholder(tf.float32)
            self.drops = tf.placeholder(tf.float32)
            self.vars = utils.init_var_map(self.init_actions, self.init_path)
            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True
            self.__sess = tf.Session(config=config)
            self.build_graph()
            tf.initialize_all_variables().run(session=self.__sess)

    def __train_batch(self, indices, values, shapes, labels):
        feed_dict = {self.y_true: labels, self.drops: self.layer_drops}
        if utils.check_type(self.get_input_spaces(), 'int'):
            feed_dict[self.x] = (indices, values, shapes)
        else:
            for i in range(len(self.x)):
                feed_dict[self.x[i]] = (indices[i], values[i], shapes[i])
        _, l, y, y_prob = self.__sess.run(fetches=[self.optimizer, self.loss, self.y, self.y_prob],
                                          feed_dict=feed_dict)
        return l, y, y_prob

    def __train_round(self, dtrain):
        indices, values, labels = dtrain
        loss, y, y_prob = [], [], []
        input_spaces = self.get_input_spaces()
        batch_size = self.batch_size
        if batch_size == -1:
            indices, values, shape = utils.libsvm_2_csr(indices, values, input_spaces)
            loss, y, y_prob = self.__train_batch(indices, values, shape, labels)
        else:
            for i in range(len(indices) / batch_size + 1):
                indices_i = indices[i * batch_size: (i + 1) * batch_size]
                values_i = values[i * batch_size: (i + 1) * batch_size]
                labels_i = labels[i * batch_size: (i + 1) * batch_size]
                indices_i, values_i, batch_shape = utils.libsvm_2_csr(indices_i, values_i, input_spaces)
                batch_loss, batch_y, batch_y_prob = self.__train_batch(indices_i, values_i, batch_shape, labels_i)
                loss.append(batch_loss)
                y.extend(batch_y)
                y_prob.extend(batch_y_prob)
        return np.array(loss), np.array(y), np.array(y_prob)

    def train(self, dtrain, dvalid=None):
        train_indices, train_values, train_labels = dtrain
        train_scores = []
        if dvalid is not None:
            valid_indices, valid_values, valid_labels = dvalid
            valid_scores = []
        for i in range(self.num_round):
            train_loss, train_y, train_y_prob = self.__train_round(dtrain)
            train_score = log_loss(train_labels, train_y_prob)
            if dvalid is not None:
                valid_y_prob = self.predict(dvalid[:2])
                valid_score = log_loss(valid_labels, valid_y_prob)
            if self.verbose:
                if dvalid is not None:
                    print '[%d]\tloss: %f \ttrain_score: %f\tvalid_score: %f' % \
                          (i, train_loss.mean(), train_score, valid_score)
                else:
                    print '[%d]\tloss: %f \ttrain_score: %f\t' % \
                          (i, train_loss.mean(), train_score)
            if self.save_log:
                if dvalid is not None:
                    log_str = '%d\t%f\t%f\t%f\n' % (i, train_loss.mean(), train_score, valid_score)
                else:
                    log_str = '%d\t%f\t%f\n' % (i, train_loss.mean(), train_score)
                self.write_log(log_str)
            train_scores.append(train_score)
            if dvalid is not None:
                valid_scores.append(valid_score)
                if utils.check_early_stop(valid_scores, self.early_stop_round, 'no_decrease'):
                    if self.verbose:
                        best_iteration = i + 1 - self.early_stop_round
                        print 'best iteration:\n[%d]\ttrain_score: %f\tvalid_score: %f' % (
                            best_iteration, train_scores[best_iteration], valid_scores[best_iteration])
                    break
        if dvalid is not None:
            print '[-1]\ttrain_score: %f\tvalid_score: %f' % (train_scores[-1], valid_scores[-1])
            return train_scores[-1], valid_scores[-1]
        else:
            print '[-1]\ttrain_score: %f' % train_scores[-1]
            return train_scores[-1]

    def __predict_batch(self, indices, values, shapes):
        feed_dict = {self.drops: [1] * len(self.layer_drops)}
        if utils.check_type(self.get_input_spaces(), 'int'):
            feed_dict[self.x] = (indices, values, shapes)
        else:
            for i in range(len(self.x)):
                feed_dict[self.x[i]] = (indices[i], values[i], shapes[i])
        y_prob = self.run(self.y_prob, feed_dict=feed_dict)
        return y_prob

    def predict(self, data):
        indices, values = data[:2]
        input_spaces = self.get_input_spaces()
        y_prob = []
        batch_size = self.batch_size
        if batch_size == -1:
            indices, values, shape = utils.libsvm_2_csr(indices, values, input_spaces)
            y_prob = self.__predict_batch(indices, values, shape)
        else:
            for i in range(len(indices) / batch_size + 1):
                indices_i = indices[i * batch_size: (i + 1) * batch_size]
                values_i = values[i * batch_size: (i + 1) * batch_size]
                indices_i, values_i, shape_i = utils.libsvm_2_csr(indices_i, values_i, input_spaces)
                y_prob_i = self.__predict_batch(indices_i, values_i, shape_i)
                y_prob.extend(y_prob_i)
        return np.array(y_prob)

    def dump(self):
        var_map = {}
        for name, var in self.vars.iteritems():
            var_map[name] = self.run(var)
        pkl.dump(var_map, open(self.get_bin_path(), 'wb'))
        print 'model dumped at', self.get_bin_path()


# class logistic_regression(tf_classifier):
#     def __init__(self, name, eval_metric, num_class, input_space, opt_algo, learning_rate, l1_w=0, l2_w=0, l2_b=0):
#         tf_classifier.__init__(self, name, eval_metric, num_class,
#                                [('w', [input_space, num_class], 'normal', tf.float32),
#                                 ('b', [num_class], 'zero', tf.float32)],
#                                opt_algo=opt_algo, learning_rate=learning_rate, l1_w=l1_w, l2_w=l2_w, l2_b=l2_b)
#
#     def build_graph(self, opt_algo, learning_rate, l1_w, l2_w, l2_b):
#         tf_classifier.build_graph(self)
#         w = self.vars['w']
#         b = self.vars['b']
#         y = tf.sparse_tensor_dense_matmul(self.x, w) + b
#         y_prob, loss = get_loss(self.get_eval_metric(), y, self.y_true)
#         loss += l1_w * get_l1_loss(w) + l2_w * tf.nn.l2_loss(w) + l2_b * tf.nn.l2_loss(b)
#         optimizer = get_optimizer(opt_algo, learning_rate, loss)
#         return y, y_prob, loss, optimizer


class FactorizationMachine(TFClassifier):
    def __init__(self, name, eval_metric, input_spaces, num_class, batch_size=None, num_round=None,
                 early_stop_round=None, verbose=True, save_log=True,
                 factor_order=None, opt_algo=None, learning_rate=None,
                 l1_w=0, l1_v=0, l2_w=0, l2_v=0, l2_b=0
                 ):
        TFClassifier.__init__(self, name, eval_metric, input_spaces, num_class, batch_size, num_round, early_stop_round,
                              verbose, save_log)
        self.init_actions = [('w', [input_spaces, num_class], 'normal', tf.float32),
                             ('v', [input_spaces, factor_order * num_class], 'normal', tf.float32),
                             ('b', [num_class], 'zero', tf.float32)],
        self.factor_order = factor_order
        self.opt_algo = opt_algo
        self.learning_rate = learning_rate,
        self.l1_w = l1_w
        self.l1_v = l1_v
        self.l2_w = l2_w
        self.l2_v = l2_v
        self.l2_b = l2_b

    def build_graph(self):
        x_square = tf.SparseTensor(self.x.indices, tf.square(self.x.values), self.x.shape)
        w = self.vars['w']
        v = self.vars['v']
        b = self.vars['b']
        self.y = tf.sparse_tensor_dense_matmul(self.x, w) + b
        self.y += tf.reduce_sum(tf.reshape(
            tf.square(tf.sparse_tensor_dense_matmul(self.x, v)) - \
            tf.sparse_tensor_dense_matmul(x_square, tf.square(v)),
            [-1, self.factor_order, self.get_num_class()]), reduction_indices=[1])
        self.y_prob, self.loss = utils.get_loss(self.get_eval_metric(), self.y, self.y_true)
        self.loss += self.l1_w * utils.get_l1_loss(w) + self.l1_v * utils.get_l1_loss(v) + \
                     self.l2_w * tf.nn.l2_loss(w) + self.l2_v * tf.nn.l2_loss(v) + self.l2_b * tf.nn.l2_loss(b)
        self.optimizer = utils.get_optimizer(self.opt_algo, self.learning_rate, self.loss)


class MultiLayerPerceptron(TFClassifier):
    def __init__(self, name, eval_metric, input_spaces, num_class,
                 batch_size=None, num_round=None, early_stop_round=None, verbose=True, save_log=True,
                 layer_sizes=None, layer_activates=None, layer_drops=None, layer_inits=None, init_path=None,
                 opt_algo=None, learning_rate=None):
        TFClassifier.__init__(self, name, eval_metric, input_spaces, num_class, batch_size=batch_size,
                              num_round=num_round, early_stop_round=early_stop_round, verbose=verbose,
                              save_log=save_log)
        self.init_actions = []
        for i in range(len(layer_sizes) - 1):
            self.init_actions.append(('w%d' % i, [layer_sizes[i], layer_sizes[i + 1]], layer_inits[i][0], tf.float32))
            self.init_actions.append(('b%d' % i, [layer_sizes[i + 1]], layer_inits[i][1], tf.float32))
        self.layer_inits = layer_inits
        self.init_path = init_path
        self.layer_activates = layer_activates
        self.layer_drops = layer_drops
        self.opt_algo = opt_algo
        self.learning_rate = learning_rate

    def build_graph(self):
        w0 = self.vars['w0']
        b0 = self.vars['b0']
        l = utils.activate(tf.sparse_tensor_dense_matmul(self.x, w0) + b0, self.layer_activates[0])
        l = tf.nn.dropout(l, keep_prob=self.drops[0])
        for i in range(1, len(self.vars) / 2):
            wi = self.vars['w%d' % i]
            bi = self.vars['b%d' % i]
            l = utils.activate(tf.matmul(l, wi) + bi, self.layer_activates[i])
            l = tf.nn.dropout(l, keep_prob=self.drops[i])
        self.y = l
        self.y_prob, self.loss = utils.get_loss(self.get_eval_metric(), l, self.y_true)
        self.optimizer = utils.get_optimizer(self.opt_algo, self.learning_rate, self.loss)


class MultiplexNeuralNetwork(TFClassifier):
    def __init__(self, name, eval_metric, input_spaces, num_class,
                 batch_size=None, num_round=None, early_stop_round=None, verbose=True, save_log=True,
                 layer_sizes=None, layer_activates=None, layer_drops=None, layer_inits=None, init_path=None,
                 opt_algo=None, learning_rate=None):
        TFClassifier.__init__(self, name, eval_metric, input_spaces, num_class, batch_size=batch_size,
                              num_round=num_round, early_stop_round=early_stop_round, verbose=verbose,
                              save_log=save_log)
        self.init_actions = []
        for i in range(len(layer_sizes[0])):
            layer_input = layer_sizes[0][i]
            layer_output = layer_sizes[1][i]
            self.init_actions.append(('w0_%d' % i, [layer_input, layer_output], layer_inits[0][0], tf.float32))
            self.init_actions.append(('b0_%d' % i, [layer_output], layer_inits[0][1], tf.float32))
        self.init_actions.append(('w1', [sum(layer_sizes[1]), layer_sizes[2]], layer_inits[1][0], tf.float32))
        self.init_actions.append(('b1', [layer_sizes[2]], layer_inits[1][1], tf.float32))
        for i in range(2, len(layer_sizes) - 1):
            layer_input = layer_sizes[i]
            layer_output = layer_sizes[i + 1]
            self.init_actions.append(('w%d' % i, [layer_input, layer_output], layer_inits[i][0], tf.float32))
            self.init_actions.append(('b%d' % i, [layer_output], layer_inits[i][1], tf.float32))
        self.layer_inits = layer_inits
        self.init_path = init_path
        self.layer_activates = layer_activates
        self.layer_drops = layer_drops
        self.opt_algo = opt_algo
        self.learning_rate = learning_rate

    def build_graph(self):
        num_input = len(self.get_input_spaces())
        w0 = [self.vars['w0_%d' % i] for i in range(num_input)]
        b0 = [self.vars['b0_%d' % i] for i in range(num_input)]
        l = tf.nn.dropout(
            utils.activate(
                tf.concat(1, [tf.sparse_tensor_dense_matmul(self.x[i], w0[i]) + b0[i] for i in range(num_input)]),
                self.layer_activates[0]), self.drops[0])
        for i in range(1, len(self.vars) / 2 - num_input + 1):
            wi = self.vars['w%d' % i]
            bi = self.vars['b%d' % i]
            l = tf.nn.dropout(utils.activate(tf.matmul(l, wi) + bi, self.layer_activates[i]), keep_prob=self.drops[i])
        self.y = l
        self.y_prob, self.loss = utils.get_loss(self.get_eval_metric(), l, self.y_true)
        self.optimizer = utils.get_optimizer(self.opt_algo, self.learning_rate, self.loss)

# class convolutional_neural_network(tf_classifier_multi):
#     def __init__(self, name, eval_metric, input_spaces, num_class, layer_sizes, layer_activates, kernel_sizes,
#                  opt_algo,
#                  learning_rate,
#                  layer_inits=None, init_path=None, layer_pools=None, layer_pool_strides=None):
#         if layer_inits is None:
#             layer_inits = [('normal', 'zero')] * (len(layer_sizes) - 1)
#         init_actions = []
#         for i in range(len(layer_sizes[0])):
#             init_actions.append(('w0_%d' % i, [layer_sizes[0][i], layer_sizes[1][i]], layer_inits[0][0], tf.float32))
#             init_actions.append(('b0_%d' % i, [layer_sizes[1][i]], layer_inits[0][1], tf.float32))
#         for i in range(len(kernel_sizes)):
#             init_actions.append(('k%d' % i, kernel_sizes[i], 'normal', tf.float32))
#         l1_input_w = len(layer_sizes[0])
#         l1_input_h = layer_sizes[1][0]
#         l1_input_c = 1
#         for i in range(len(kernel_sizes)):
#             w, h, ci, co = kernel_sizes[i]
#             l1_input_w -= (w - 1)
#             l1_input_h -= (h - 1)
#             l1_input_w /= layer_pool_strides[i][1]
#             l1_input_h /= layer_pool_strides[i][2]
#             l1_input_c = co
#         l1_input_size = l1_input_w * l1_input_h * l1_input_c
#         init_actions.append(('w1', [l1_input_size, layer_sizes[2]], layer_inits[1][0], tf.float32))
#         init_actions.append(('b1', [layer_sizes[2]], layer_inits[1][1], tf.float32))
#         for i in range(2, len(layer_sizes) - 1):
#             init_actions.append(('w%d' % i, [layer_sizes[i], layer_sizes[i + 1]], layer_inits[i][0], tf.float32))
#             init_actions.append(('b%d' % i, [layer_sizes[i + 1]], layer_inits[i][1], tf.float32))
#         print init_actions
#         tf_classifier_multi.__init__(self, name, eval_metric, input_spaces, num_class,
#                                      init_actions=init_actions,
#                                      init_path=init_path,
#                                      layer_activates=layer_activates,
#                                      layer_pools=layer_pools,
#                                      layer_pool_strides=layer_pool_strides,
#                                      opt_algo=opt_algo,
#                                      learning_rate=learning_rate, )
#
#     def build_graph(self, layer_activates, layer_pools, layer_pool_strides, opt_algo, learning_rate):
#         num_input = len(self.get_input_spaces())
#         w0 = [self.vars['w0_%d' % i] for i in range(num_input)]
#         b0 = [self.vars['b0_%d' % i] for i in range(num_input)]
#         l = [tf.reshape(tf.sparse_tensor_dense_matmul(self.x[i], w0[i]) + b0[i],
#                           [tf.shape(self.x[i])[0], 1, -1, 1]) for
#              i in range(num_input)]
#         l = activate(tf.concat(1, l), layer_activates[0])
#         for i in range(len(layer_pools)):
#             l = tf.nn.conv2d(l, self.vars['k%d' % i], strides=[1, 1, 1, 1], padding='VALID')
#             if layer_pools is not None:
#                 l = tf.nn.max_pool(l, layer_pools[i], strides=layer_pool_strides[i], padding='VALID')
#         l = tf.nn.dropout(l, self.drops[0])
#         l = tf.reshape(l, [tf.shape(self.x[0])[0], -1])
#         for i in range(1, (len(self.vars) - len(layer_pools)) / 2 - num_input + 1):
#             wi = self.vars['w%d' % i]
#             bi = self.vars['b%d' % i]
#             l = tf.nn.dropout(activate(tf.matmul(l, wi) + bi, layer_activates[i]), keep_prob=self.drops[i])
#         y_prob, loss = get_loss(self.get_eval_metric(), l, self.y_true)
#         optimizer = get_optimizer(opt_algo, learning_rate, loss)
#         return l, y_prob, loss, optimizer


# class text_convolutional_neural_network(tf_classifier):
#     def __init__(self, name, eval_metric, input_spaces, num_class, layer_sizes, layer_activates, kernel_depth,
#                   opt_algo,
#                  learning_rate,
#                  layer_inits=None, kernel_inits=None, init_path=None):
#         if layer_inits is None:
#             layer_inits = [('normal', 'zero')] * (len(layer_sizes) - 1)
#         init_actions = []
#         for i in range(len(layer_sizes[0])):
#             init_actions.append(('w0_%d' % i, [layer_sizes[0][i], layer_sizes[1][i]], layer_inits[0][0], tf.float32))
#             init_actions.append(('b0_%d' % i, [layer_sizes[1][i]], layer_inits[0][1], tf.float32))
#         for i in range(len(layer_sizes[0])):
#             init_actions.append(
#                 ('k%d' % i, [i + 1, layer_sizes[1][0], 1, kernel_depth], kernel_inits[i][0], tf.float32))
#             init_actions.append(('kb%d' % i, [kernel_depth], kernel_inits[i][1], tf.float32))
#         init_actions.append(('w1', [len(layer_sizes[0]) * kernel_depth, layer_sizes[2]],
#                               layer_inits[1][0], tf.float32))
#         init_actions.append(('b1', [layer_sizes[2]], layer_inits[1][1], tf.float32))
#         for i in range(2, len(layer_sizes) - 1):
#             init_actions.append(('w%d' % i, [layer_sizes[i], layer_sizes[i + 1]], layer_inits[i][0], tf.float32))
#             init_actions.append(('b%d' % i, [layer_sizes[i + 1]], layer_inits[i][1], tf.float32))
#         print init_actions
#         tf_classifier_multi.__init__(self, name, eval_metric, input_spaces, num_class,
#                                      init_actions=init_actions,
#                                      init_path=init_path,
#                                      layer_activates=layer_activates,
#                                      kernel_depth=kernel_depth,
#                                      opt_algo=opt_algo,
#                                      learning_rate=learning_rate, )
#
#     def build_graph(self, layer_activates, kernel_depth, opt_algo, learning_rate):
#         num_input = len(self.get_input_spaces())
#         w0 = [self.vars['w0_%d' % i] for i in range(num_input)]
#         b0 = [self.vars['b0_%d' % i] for i in range(num_input)]
#         l = [tf.reshape(tf.sparse_tensor_dense_matmul(self.x[i], w0[i]) + b0[i],
#                           [tf.shape(self.x[i])[0], 1, -1, 1]) for
#              i in range(num_input)]
#         l = activate(tf.concat(1, l), layer_activates[0])
#         print 0, layer_activates[0]
#         l_arr = []
#         for i in range(len(self.x)):
#             li = tf.nn.conv2d(l, self.vars['k%d' % i], strides=[1, 1, 1, 1], padding='VALID')
#             li = tf.nn.bias_add(li, self.vars['kb%d' % i])
#             li = tf.nn.max_pool(li, [1, len(self.x) - i, 1, 1], strides=[1, 1, 1, 1], padding='VALID')
#             l_arr.append(li)
#         l = tf.concat(1, l_arr)
#         l = tf.reshape(l, [-1, len(self.x) * kernel_depth])
#         l = tf.nn.dropout(l, self.drops[0])
#         for i in range(1, len(self.vars) / 2 - len(self.x) - num_input + 1):
#             wi = self.vars['w%d' % i]
#             bi = self.vars['b%d' % i]
#             print i, layer_activates[i]
#             l = tf.nn.dropout(activate(tf.matmul(l, wi) + bi, layer_activates[i]), keep_prob=self.drops[i])
#         y_prob, loss = get_loss(self.get_eval_metric(), l, self.y_true)
#         optimizer = get_optimizer(opt_algo, learning_rate, loss)
#         return l, y_prob, loss, optimizer
#         # return None, None, None, None
