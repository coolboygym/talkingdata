import cPickle as pkl
import random
import time

import numpy as np

import feature

data_app_events = '../data/raw/app_events.csv'
data_app_labels = '../data/raw/app_labels.csv'
data_events = '../data/raw/events.csv'
data_gender_age_test = '../data/raw/gender_age_test.csv'
data_gender_age_train = '../data/raw/gender_age_train.csv'
data_label_categories = '../data/raw/label_categories.csv'
data_phone_brand_device_model = '../data/raw/phone_brand_device_model.csv'
data_sample_submission = '../data/raw/sample_submission.csv'


def read_data():
    dict_device = pkl.load(open('../data/dict_id_device.pkl', 'rb'))

    groups = ['F23-', 'F24-26', 'F27-28', 'F29-32', 'F33-42', 'F43+', 'M22-', 'M23-26', 'M27-28', 'M29-31', 'M32-38',
              'M39+']
    group_id = {}
    for i, v in enumerate(groups):
        group_id[v] = i

    train_data = np.loadtxt(data_gender_age_train, delimiter=',', skiprows=1, usecols=[0, 3],
                            dtype=[('device_id', np.int64), ('group', 'S10')])
    test_data = np.loadtxt(data_gender_age_test, delimiter=',', skiprows=1, dtype=np.int64)

    train_device_id = map(lambda d: dict_device[d], train_data['device_id'])
    train_label = map(lambda d: group_id[d], train_data['group'])
    test_device_id = map(lambda d: dict_device[d], test_data)
    return train_device_id, train_label, test_device_id


def gather_device_id():
    train_device_id, _, test_device_id = read_data()
    print len(train_device_id)
    train_size = len(train_device_id)

    device_id = train_device_id
    device_id.extend(test_device_id)
    device_id = np.array(device_id)
    print device_id, device_id.shape

    np.savetxt('../feature/device_id', device_id, header='%d' % train_size, fmt='%d')


def gather_event_id():
    train_device_id, _, test_device_id = read_data()

    dict_device_event = pkl.load(open('../data/dict_device_event.pkl'))
    device_event_id = []
    for did in train_device_id:
        if did in dict_device_event:
            eids = map(lambda x: x[0], dict_device_event[did])
            device_event_id.extend(map(lambda x: [did, x], eids))
    train_size = len(device_event_id)
    for did in test_device_id:
        if did in dict_device_event:
            eids = map(lambda x: x[0], dict_device_event[did])
            device_event_id.extend(map(lambda x: [did, x], eids))

    device_event_id = np.array(device_event_id)
    print device_event_id, device_event_id.shape

    np.savetxt('../feature/device_event_id', device_event_id, header='%d ' % train_size, fmt='%d')


# gather_event_id()


fea_phone_brand = feature.one_hot_feature(name='phone_brand', dtype='d')
fea_device_model = feature.one_hot_feature(name='device_model', dtype='d')
fea_installed_app = feature.multi_feature(name='installed_app', dtype='d')
fea_active_app = feature.multi_feature(name='active_app', dtype='d')
fea_installed_app_norm = feature.multi_feature(name='installed_app_norm', dtype='f')
fea_active_app_norm = feature.multi_feature(name='active_app_norm', dtype='f')
fea_event_time = feature.multi_feature(name='event_time', dtype='d')
fea_event_longitude = feature.num_feature(name='event_longitude', dtype='f')
fea_event_longitude_norm = feature.num_feature(name='event_longitude_norm', dtype='f')
fea_event_latitude = feature.num_feature(name='event_latitude', dtype='f')
fea_event_latitude_norm = feature.num_feature(name='event_latitude_norm', dtype='f')
fea_event_phone_brand = feature.one_hot_feature(name='event_phone_brand', dtype='d')
fea_event_installed_app = feature.multi_feature(name='event_installed_app', dtype='d')
fea_event_installed_app_norm = feature.multi_feature(name='event_installed_app_norm', dtype='f')


def make_feature():
    print 'loading data...'
    start_time = time.time()

    dict_device_brand_model = pkl.load(open('../data/dict_device_brand_model.pkl', 'rb'))
    # dict_device_event = pkl.load(open('../data/dict_device_event.pkl', 'rb'))
    dict_app_event = pkl.load(open('../data/dict_app_event.pkl', 'rb'))
    # dict_brand = pkl.load(open('../data/dict_id_brand.pkl', 'rb'))
    # dict_model = pkl.load(open('../data/dict_id_model.pkl', 'rb'))
    # dict_app = pkl.load(open('../data/dict_id_app.pkl', 'rb'))
    dict_event = pkl.load(open('../data/dict_event.pkl', 'rb'))

    print 'finish in %d sec' % (time.time() - start_time)

    # device_id = np.loadtxt('../feature/device_id', dtype=np.int64, skiprows=1)
    #
    # fea_phone_brand.process(device_id=device_id, dict_device_brand_model=dict_device_brand_model)
    # fea_phone_brand.dump()
    #
    # fea_device_model.process(device_id=device_id, dict_device_brand_model=dict_device_brand_model)
    # fea_device_model.dump()
    #
    # fea_installed_app.process(device_id=device_id, dict_device_event=dict_device_event, dict_app_event=dict_app_event)
    # fea_installed_app.dump()
    #
    # indices, values = fea_installed_app.get_value()
    # fea_installed_app_norm.process(indices=indices, values=values)
    # fea_installed_app_norm.dump()
    #
    # fea_active_app.process(device_id=device_id, dict_device_event=dict_device_event, dict_app_event=dict_app_event)
    # fea_active_app.dump()
    #
    # indices, values = fea_active_app.get_value()
    # fea_active_app_norm.process(indices=indices, values=values)
    # fea_active_app_norm.dump()

    event_id = np.loadtxt('../feature/device_event_id', dtype=np.int64, skiprows=1, usecols=[1])

    # fea_event_time.process(event_id=event_id, dict_event=dict_event)
    # fea_event_time.dump()

    # fea_event_longitude.process(event_id=event_id, dict_event=dict_event)
    # fea_event_longitude.dump()
    #
    # indices, values = fea_event_longitude.get_value()
    # print np.max(values), np.min(values)
    #
    # fea_event_longitude_norm.process(indices=indices, values=values)
    # fea_event_longitude_norm.dump()
    #
    # fea_event_latitude.process(event_id=event_id, dict_event=dict_event)
    # fea_event_latitude.dump()
    #
    # indices, values = fea_event_latitude.get_value()
    # print np.max(values), np.min(values)
    #
    # fea_event_latitude_norm.process(indices=indices, values=values)
    # fea_event_latitude_norm.dump()
    fea_event_phone_brand.process(event_id=event_id, dict_event=dict_event,
                                  dict_device_brand_model=dict_device_brand_model)
    fea_event_phone_brand.dump()

    fea_event_installed_app.process(event_id=event_id, dict_app_event=dict_app_event)
    fea_event_installed_app.dump()

    indices, values = fea_event_installed_app.get_value()
    fea_event_installed_app_norm.process(indices=indices, values=values)
    fea_event_installed_app_norm.dump()


make_feature()


def concat_feature(name, fea_list):
    extra = ','.join([fea.get_name() for fea in fea_list])
    print 'concat feature list', extra

    print 'loading features...'
    start_time = time.time()

    spaces = []
    for fea in fea_list:
        fea.load()
        spaces.append(fea.get_space())

    print 'finish in %d sec' % (time.time() - start_time)
    print 'spaces', str(spaces)

    fea_concat = feature.multi_feature(name=name, dtype='f')

    collect_indices = []
    collect_values = []

    for i in range(len(fea_list)):
        fea = fea_list[i]
        concat_indices, concat_values = fea.get_value()
        concat_indices += sum(spaces[:i])
        collect_indices.append(concat_indices)
        collect_values.append(concat_values)

    concat_indices = []
    concat_values = []
    for i in range(fea_list[0].get_size()):
        tmp_indices = []
        tmp_values = []
        for j in range(len(fea_list)):
            tmp_indices.extend(feature.get_array(collect_indices[j][i]))
            tmp_values.extend(feature.get_array(collect_values[j][i]))
        concat_indices.append(np.array(tmp_indices))
        concat_values.append(np.array(tmp_values))

    concat_indices = np.array(concat_indices)
    concat_values = np.array(concat_values)

    print concat_indices
    print concat_values

    fea_concat.set_value(indices=concat_indices, values=concat_values)
    max_indices = map(feature.get_max, concat_indices)
    len_indices = map(lambda x: len(x), concat_values)
    fea_concat.set_space(max(max_indices) + 1)
    fea_concat.set_rank(max(len_indices))
    fea_concat.set_size(len(concat_indices))

    fea_concat.dump(extra=extra)


# concat_feature('concat_5', [fea_device_model, fea_active_app_norm])

# fea_concat_1 = feature.multi_feature(name='concat_1')
# fea_concat_1.load()
# print fea_concat_1.get_value()
# print fea_concat_1.get_name()
# print fea_concat_1.get_feature_type()
# print fea_concat_1.get_data_type()
# print fea_concat_1.get_space()
# print fea_concat_1.get_rank()
# print fea_concat_1.get_size()
#
# fea_concat_2 = feature.multi_feature(name='concat_2')
# fea_concat_2.load()
# print fea_concat_2.get_value()
#
# fea_concat_3 = feature.multi_feature(name='concat_3')
# fea_concat_3.load()
# print fea_concat_3.get_value()


def split_dataset(name, nfold):
    _, train_label, _ = read_data()

    with open('../feature/' + name, 'r') as data_in:
        next(data_in)
        with open('../feature/device_id', 'r') as device_id_in:
            train_size = int(device_id_in.readline().strip().split()[1])

        with open('../input/' + name + '.train', 'w') as train_out:
            for i in range(train_size):
                train_out.write('%d %s' % (train_label[i], next(data_in)))

        with open('../input/' + name + '.test', 'w') as test_out:
            for line in data_in:
                test_out.write('0 %s' % line)

    folds = [[] for i in range(nfold)]
    cv_rate = 1.0 / nfold
    with open('../input/' + name + '.train', 'r') as train_in:
        for line in train_in:
            folds[int(random.random() / cv_rate)].append(line)

    for i in range(nfold):
        with open('../input/' + name + '.train.%d.valid' % i, 'w') as fout:
            for line in folds[i]:
                fout.write(line)

        with open('../input/' + name + '.train.%d.train' % i, 'w') as fout:
            for j in range(nfold):
                if j != i:
                    for line in folds[j]:
                        fout.write(line)


# unify feature numbers in the ../feature/concat for gym's xgb use
def unify_feature_numbers(name):
    path_input = '../feature/' + name
    path_output = '../feature/' + name + '_unify'
    with open(path_input) as fin:
        with open(path_output, 'w') as fout:
            i = 0
            for line in fin:
                if i == 0:
                    fout.write(line)
                else:
                    fout.write('40270:0.0 ' + line)
                i += 1


split_dataset('concat_3_unify', 5)
# unify_feature_numbers('concat_3')
