import cPickle as pkl

# import tensorflow as tf

from model import *


class opt_property:
    def __init__(self, name, learning_rate):
        self.name = name
        self.learning_rate = learning_rate


class gd_property(opt_property):
    def __init__(self, learning_rate):
        opt_property.__init__(self, 'gd', learning_rate)


class ftrl_property(opt_property):
    def __init__(self, learning_rate,
                 learning_rate_power=-0.5,
                 initial_accumulator_value=0.1,
                 l1_regularization_strength=0.0,
                 l2_regularization_strength=0.0):
        opt_property.__init__(self, 'ftrl', learning_rate)
        self.learning_rate_power = learning_rate_power
        self.initial_accumulator_value = initial_accumulator_value
        self.l1_regularization_strength = l1_regularization_strength
        self.l2_regularization_strength = l2_regularization_strength


class adagrad_property(opt_property):
    def __init__(self, learning_rate, initial_accumulator_value=0.1):
        opt_property.__init__(self, 'adagrad', learning_rate)
        self.initial_accumulator_value = initial_accumulator_value


class adadelta_property(opt_property):
    def __init__(self, learning_rate=0.001, rho=0.95, epsilon=1e-8, ):
        opt_property.__init__(self, 'adadelta', learning_rate)
        self.rho = rho
        self.epsilon = epsilon


def init_var_map(init_actions, init_path=None, stddev=0.01, minval=-0.01, maxval=0.01):
    if init_path is not None:
        var_map = pkl.load(open(init_path, 'rb'))
        print 'init variable from', init_path
    else:
        var_map = {}
    for var_name, var_shape, init_method, dtype in init_actions:
        if var_name in var_map:
            print var_name, 'already exists'
        else:
            if init_method == 'zero':
                var_map[var_name] = tf.Variable(tf.zeros(var_shape, dtype=dtype), dtype=dtype)
            elif init_method == 'one':
                var_map[var_name] = tf.Variable(tf.ones(var_shape, dtype=dtype), dtype=dtype)
            elif init_method == 'normal':
                var_map[var_name] = tf.Variable(tf.random_normal(var_shape, mean=0.0, stddev=stddev, dtype=dtype),
                                                dtype=dtype)
            elif init_method == 'uniform':
                var_map[var_name] = tf.Variable(tf.random_uniform(var_shape, minval=minval, maxval=maxval, dtype=dtype),
                                                dtype=dtype)
            else:
                print 'BadParam: init method', init_method
    return var_map


def get_loss(loss_func, y, y_true):
    if loss_func == 'sigmoid_log_loss':
        y_prob = tf.nn.sigmoid(y)
        loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(y, y_true))
    elif loss_func == 'softmax_log_loss':
        y_prob = tf.nn.softmax(y)
        loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(y, y_true))
    else:
        y_prob = tf.nn.sigmoid(y)
        loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(y, y_true))
    return y_prob, loss


def get_optimizer(opt_prop, loss):
    if opt_prop.name == 'adaldeta':
        if not isinstance(opt_prop, adadelta_property):
            opt_prop = adadelta_property(opt_prop.learning_rate)
        return tf.train.AdadeltaOptimizer(learning_rate=opt_prop.learning_rate,
                                          rho=opt_prop.rho,
                                          epsilon=opt_prop.epsilon).minimize(loss)
    elif opt_prop.name == 'adagrad':
        if not isinstance(opt_prop, adagrad_property):
            opt_prop = adagrad_property(opt_prop.learning_rate)
        return tf.train.AdagradOptimizer(learning_rate=opt_prop.learning_rate,
                                         initial_accumulator_value=opt_prop.initial_accumulator_value).minimize(loss)
    elif opt_prop.name == 'adam':
        return tf.train.AdamOptimizer(opt_prop.learning_rate).minimize(loss)
    elif opt_prop.name == 'ftrl':
        if not isinstance(opt_prop, ftrl_property):
            opt_prop = ftrl_property(opt_prop.learning_rate)
        return tf.train.FtrlOptimizer(learning_rate=opt_prop.learning_rate,
                                      learning_rate_power=opt_prop.learning_rate_power,
                                      initial_accumulator_value=opt_prop.initial_accumulator_value,
                                      l1_regularization_strength=opt_prop.l1_regularization_strength,
                                      l2_regularization_strength=opt_prop.l2_regularization_strength).minimize(loss)
    elif opt_prop.name == 'gd':
        return tf.train.GradientDescentOptimizer(opt_prop.learning_rate).minimize(loss)
    elif opt_prop.name == 'padagrad':
        return tf.train.ProximalAdagradOptimizer(opt_prop.learning_rate).minimize(loss)
    elif opt_prop.name == 'pgd':
        return tf.train.ProximalGradientDescentOptimizer(opt_prop.learning_rate).minimize(loss)
    elif opt_prop.name == 'rmsprop':
        return tf.train.RMSPropOptimizer(opt_prop.learning_rate).minimize(loss)
    else:
        return tf.train.GradientDescentOptimizer(opt_prop.learning_rate).minimize(loss)


def get_l1_loss(weights):
    return tf.reduce_sum(tf.abs(weights))


def activate(weights, activation_function):
    if activation_function == 'sigmoid':
        return tf.nn.sigmoid(weights)
    elif activation_function == 'softmax':
        return tf.nn.softmax(weights)
    elif activation_function == 'relu':
        return tf.nn.relu(weights)
    elif activation_function == 'tanh':
        return tf.nn.tanh(weights)
    elif activation_function == 'elu':
        return tf.nn.elu(weights)
    elif activation_function == 'none':
        return weights
    else:
        return weights


class tf_classifier(classifier):
    def __init__(self, name, eval_metric, num_class, init_actions, init_path=None, stddev=0.01, minval=-0.01,
                 maxval=0.01, **argv):
        classifier.__init__(self, name, eval_metric, num_class)
        self.__graph = tf.Graph()
        with self.__graph.as_default():
            self.x = tf.sparse_placeholder(tf.float32)
            self.y_true = tf.placeholder(tf.float32)
            self.drops = tf.placeholder(tf.float32)
            self.vars = init_var_map(init_actions, init_path, stddev=stddev, minval=minval, maxval=maxval)
            self.__sess = tf.Session()
            self.y, self.y_prob, self.loss, self.optimizer = self.build_graph(**argv)
            tf.initialize_all_variables().run(session=self.__sess)

    def __del__(self):
        self.__sess.close()

    def build_graph(self, **argv):
        # return None, None, None, None
        pass

    def get_graph(self):
        return self.__graph

    def get_sess(self):
        return self.__sess

    def run(self, fetches, feed_dict=None):
        return self.__sess.run(fetches, feed_dict)

    def train(self, indices, values, shape, labels, drops=0):
        _, l, y, y_prob = self.run(fetches=[self.optimizer, self.loss, self.y, self.y_prob],
                                   feed_dict={self.x: (indices, values, shape), self.y_true: labels,
                                              self.drops: drops})
        return l, y, y_prob

    def predict(self, indices, values, shape, drops=0):
        return self.run([self.y, self.y_prob], feed_dict={self.x: (indices, values, shape), self.drops: drops})

    def dump(self, path_dump):
        var_map = {}
        for name, var in self.vars():
            var_map[name] = self.run(var)
        pkl.dump(var_map, open(self.get_bin_path(), 'wb'))
        print 'model dumped at', self.get_bin_path()


class logistic_regression(tf_classifier):
    def __init__(self, name, eval_metric, num_class, input_space, opt_prop, l1_w=0, l2_w=0, l2_b=0):
        tf_classifier.__init__(self, name, eval_metric, num_class,
                               [('w', [input_space, num_class], 'normal', tf.float32),
                                ('b', [num_class], 'zero', tf.float32)],
                               opt_prop=opt_prop, l1_w=l1_w, l2_w=l2_w, l2_b=l2_b)

    def build_graph(self, opt_prop, l1_w, l2_w, l2_b):
        tf_classifier.build_graph(self)
        w = self.vars['w']
        b = self.vars['b']
        y = tf.sparse_tensor_dense_matmul(self.x, w) + b
        y_prob, loss = get_loss(self.get_eval_metric(), y, self.y_true)
        loss += l1_w * get_l1_loss(w) + l2_w * tf.nn.l2_loss(w) + l2_b * tf.nn.l2_loss(b)
        optimizer = get_optimizer(opt_prop, loss)
        return y, y_prob, loss, optimizer


class factorization_machine(tf_classifier):
    def __init__(self, name, eval_metric, num_class, input_space, factor_order, opt_prop, l1_w=0, l1_v=0, l2_w=0,
                 l2_v=0, l2_b=0, ):
        tf_classifier.__init__(self, name, eval_metric, num_class,
                               init_actions=[('w', [input_space, num_class], 'normal', tf.float32),
                                             ('v', [input_space, factor_order * num_class], 'normal', tf.float32),
                                             ('b', [num_class], 'zero', tf.float32)], stddev=0.0001,
                               factor_order=factor_order, opt_prop=opt_prop,
                               l1_w=l1_w, l1_v=l1_v, l2_w=l2_w, l2_v=l2_v, l2_b=l2_b)

    def build_graph(self, factor_order, opt_prop, l1_w, l1_v, l2_w, l2_v, l2_b):
        tf_classifier.build_graph(self, )
        x_square = tf.SparseTensor(self.x.indices, tf.square(self.x.values), self.x.shape)
        w = self.vars['w']
        v = self.vars['v']
        b = self.vars['b']
        y = tf.sparse_tensor_dense_matmul(self.x, w) + b
        y += tf.reduce_sum(tf.reshape(
            tf.square(tf.sparse_tensor_dense_matmul(self.x, v)) - tf.sparse_tensor_dense_matmul(x_square, tf.square(v)),
            [-1, factor_order, self.get_num_class()]), reduction_indices=[1])
        y_prob, loss = get_loss(self.get_eval_metric(), y, self.y_true)
        loss += l1_w * get_l1_loss(w) + l1_v * get_l1_loss(v) + l2_w * tf.nn.l2_loss(w) + l2_v * tf.nn.l2_loss(
            v) + l2_b * tf.nn.l2_loss(b)
        optimizer = get_optimizer(opt_prop, loss)
        return y, y_prob, loss, optimizer


class multi_layer_perceptron(tf_classifier):
    def __init__(self, name, eval_metric, layer_sizes, layer_activates, opt_prop):
        init_actions = []
        for i in range(len(layer_sizes) - 1):
            init_actions.append(('w%d' % i, [layer_sizes[i], layer_sizes[i + 1]], 'normal', tf.float32))
            init_actions.append(('b%d' % i, [layer_sizes[i + 1]], 'zero', tf.float32))
        tf_classifier.__init__(self, name, eval_metric, layer_sizes[-1],
                               init_actions=init_actions, stddev=0.01,
                               layer_activates=layer_activates, opt_prop=opt_prop)

    def build_graph(self, layer_activates, opt_prop):
        tf_classifier.build_graph(self)
        w0 = self.vars['w0']
        b0 = self.vars['b0']
        # self.dropouts = tf.placeholder(dtype=tf.float32, shape=[None])
        l = activate(tf.sparse_tensor_dense_matmul(self.x, w0) + b0, layer_activates[0])
        for i in range(1, len(self.vars) / 2):
            wi = self.vars['w%d' % i]
            bi = self.vars['b%d' % i]
            l = activate(tf.matmul(tf.nn.dropout(l, keep_prob=self.drops[i - 1]), wi) + bi, layer_activates[i])
        y_prob, loss = get_loss(self.get_eval_metric(), l, self.y_true)
        optimizer = get_optimizer(opt_prop, loss)
        return l, y_prob, loss, optimizer
