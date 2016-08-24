import time

import xgboost as xgb

import feature
import utils
from model_impl import GBLinear, GBTree, MultiLayerPerceptron, MultiplexNeuralNetwork


class Task:
    def __init__(self, dataset, booster, version,
                 input_type=None,
                 sub_input_types=None,
                 eval_metric='softmax_log_loss',
                 random_state=0,
                 num_class=12,
                 train_size=59716,
                 valid_size=14929,
                 test_size=112071):
        self.dataset = dataset
        self.booster = booster
        self.version = version
        self.eval_metric = eval_metric
        self.random_state = random_state
        self.path_train = '../input/' + dataset + '.train'
        self.path_test = '../input/' + dataset + '.test'
        self.path_train_train = self.path_train + '.train'
        self.path_train_valid = self.path_train + '.valid'
        self.tag = '%s_%s_%d' % (dataset, booster, version)
        print 'initializing task', self.tag
        self.path_log = '../model/' + self.tag + '.log'
        self.path_bin = '../model/' + self.tag + '.bin'
        self.path_dump = '../model/' + self.tag + '.dump'
        self.path_submission = '../output/' + self.tag + '.submission'
        fea_tmp = feature.multi_feature(name=dataset)
        fea_tmp.load_meta()
        self.space = fea_tmp.get_space()
        self.rank = fea_tmp.get_rank()
        self.input_type = input_type
        self.sub_input_types = sub_input_types
        if self.input_type is None:
            if self.space == self.rank:
                self.input_type = 'dense'
            else:
                self.input_type = 'sparse'
        self.size = fea_tmp.get_size()
        self.train_size = train_size
        self.valid_size = valid_size
        self.test_size = test_size
        self.num_class = num_class
        if fea_tmp.load_meta_extra():
            self.sub_features = fea_tmp.get_sub_features()
            self.sub_spaces = fea_tmp.get_sub_spaces()
            self.sub_ranks = fea_tmp.get_sub_ranks()
            if self.sub_input_types is None:
                self.sub_input_types = []
                for i in range(len(self.sub_features)):
                    if self.sub_spaces[i] == self.sub_ranks[i]:
                        self.sub_input_types.append('dense')
                    else:
                        self.sub_input_types.append('sparse')
        print 'feature space: %d, rank: %d, size: %d, num class: %d' % (
            self.space, self.rank, self.size, self.num_class)

    def upgrade_version(self, offset=1, version=None):
        if version is None:
            self.version += offset
        else:
            self.version = version
        self.tag = '%s_%s_%d' % (self.dataset, self.booster, self.version)
        print 'upgrading task version', self.tag
        self.path_log = '../model/' + self.tag + '.log'
        self.path_bin = '../model/' + self.tag + '.bin'
        self.path_dump = '../model/' + self.tag + '.dump'
        self.path_submission = '../output/' + self.tag + '.submission'

    def __write_log(self, log_str):
        with open(self.path_log, 'a') as fout:
            fout.write(log_str)

    def load_data(self, path, batch_size=-1, num_class=None):
        start_time = time.time()
        if num_class is None:
            num_class = self.num_class
        if self.booster in {'gblinear', 'gbtree'}:
            data = xgb.DMatrix(path)
        elif self.booster in {'mlp'}:
            indices, values, labels = utils.read_feature(open(path), batch_size, num_class)
            data = [utils.libsvm_2_feature(indices, values, self.space, self.input_type), labels]
        elif self.booster in {'mnn'}:
            indices, values, labels = utils.read_feature(open(path), batch_size, num_class)
            split_indices, split_values = utils.split_feature(indices, values, self.sub_spaces)
            features = utils.libsvm_2_feature(split_indices, split_values, self.sub_spaces, self.sub_input_types)
            data = [features, labels]
        print 'load data', path, time.time() - start_time
        return data

    def tune(self, dtrain=None, dvalid=None, params=None, batch_size=None, num_round=None, early_stop_round=None,
             verbose=True, save_log=True, save_model=False, dtest=None, save_feature=False):
        if dtrain is None:
            dtrain = self.load_data(self.path_train_train)
        if dvalid is None:
            dvalid = self.load_data(self.path_train_valid)
        if save_feature and dtest is None:
            dtest = self.load_data(self.path_test)

        if self.booster == 'gblinear':
            print 'params [batch_size, save_log] will not be used'
            model = GBLinear(self.tag, self.eval_metric, self.space, self.num_class,
                             num_round=num_round,
                             early_stop_round=early_stop_round,
                             verbose=verbose,
                             **params)
        elif self.booster == 'gbtree':
            print 'params [batch_size, save_log] will not be used'
            model = GBTree(self.tag, self.eval_metric, self.space, self.num_class,
                           num_round=num_round,
                           early_stop_round=early_stop_round,
                           verbose=verbose,
                           **params)
        elif self.booster == 'mlp':
            start_time = time.time()
            model = MultiLayerPerceptron(self.tag, self.eval_metric, self.space, self.input_type, self.num_class,
                                         batch_size=batch_size,
                                         num_round=num_round,
                                         early_stop_round=early_stop_round,
                                         verbose=verbose,
                                         save_log=save_log,
                                         **params)
            model.compile()
            print 'build graph', time.time() - start_time
        elif self.booster == 'mnn':
            start_time = time.time()
            model = MultiplexNeuralNetwork(self.tag, self.eval_metric, self.sub_spaces, self.sub_input_types,
                                           self.num_class,
                                           batch_size=batch_size,
                                           num_round=num_round,
                                           early_stop_round=early_stop_round,
                                           verbose=verbose,
                                           save_log=save_log,
                                           **params)
            model.compile()
            print 'build graph', time.time() - start_time

        start_time = time.time()
        model.train(dtrain, dvalid)
        print 'training time elapsed: %f' % (time.time() - start_time)

        if save_model:
            model.dump()
        if save_feature:
            train_pred = model.predict(dtrain[0])
            valid_pred = model.predict(dtest[0])
            test_pred = model.predict(dtest[0])
            utils.make_feature_model_output(self.tag, [train_pred, valid_pred, test_pred], self.num_class)

    def train(self, dtrain=None, dtest=None, params=None, batch_size=None, num_round=None, verbose=True,
              save_log=True, save_model=False, save_submission=True):
        if dtrain is None:
            dtrain = self.load_data(self.path_train)
        if dtest is None:
            dtest = self.load_data(self.path_test)
        if self.booster == 'gblinear':
            print 'param [batch_size] will not be used'
            model = GBLinear(self.tag, self.eval_metric, self.space, self.num_class,
                             num_round=num_round,
                             verbose=verbose,
                             **params)
        elif self.booster == 'gbtree':
            print 'param [batch_size] will not be used'
            model = GBTree(self.tag, self.eval_metric, self.space, self.num_class,
                           num_round=num_round,
                           verbose=verbose,
                           **params)
        elif self.booster == 'mlp':
            start_time = time.time()
            model = MultiLayerPerceptron(self.tag, self.eval_metric, self.space, self.input_type, self.num_class,
                                         batch_size=batch_size,
                                         num_round=num_round,
                                         verbose=verbose,
                                         save_log=save_log,
                                         **params)
            model.compile()
            print 'build graph', time.time() - start_time
        elif self.booster == 'mnn':
            start_time = time.time()
            model = MultiplexNeuralNetwork(self.tag, self.eval_metric, self.sub_spaces, self.sub_input_types,
                                           self.num_class,
                                           batch_size=batch_size,
                                           num_round=num_round,
                                           verbose=verbose,
                                           save_log=save_log,
                                           **params)
            model.compile()
            print 'build graph', time.time() - start_time

        start_time = time.time()
        model.train(dtrain)
        print 'time elapsed: %f' % (time.time() - start_time)

        if save_model:
            model.dump()
        if save_submission:
            test_pred = model.predict(dtest[0])
            utils.make_submission(self.path_submission, test_pred)

    def predict_mlpmodel(self, data=None, params=None, batch_size=None):
        data = utils.libsvm_2_csr(data[0], data[1], self.space)
        model = MultiLayerPerceptron(self.tag, self.eval_metric, self.space, self.input_type, self.num_class,
                                     batch_size=batch_size,
                                     **params)
        model.compile()
        data_pred = model.predict(data)
        # values = data_pred
        # indices = np.zeros_like(values, dtype=np.int64) + range(self.num_class)
        # fea_pred = feature.multi_feature(name=self.tag, dtype='f', space=self.num_class, rank=self.num_class,
        #                                  size=len(indices))
        # fea_pred.set_value(indices, values)
        # fea_pred.dump()
        utils.make_feature_model_output(self.tag, [data_pred], self.num_class, dump=True)
