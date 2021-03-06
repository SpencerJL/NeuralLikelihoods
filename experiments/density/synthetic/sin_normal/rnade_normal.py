from skopt.space import Categorical

from conf import conf
from data import registry
from experiment.early_stop import EarlyStop
from experiment.experiment import Experiment
from experiment.hyper_param_opt import GridSearch
from models.tensorflow.model import Model
from models.tensorflow.tf_train_eval import TfTrainEvalModelFactory

if __name__ == '__main__':
    exp = Experiment('density/synthetic/sin_normal')

    conf.num_workers = 4
    conf.visible_device_list = [0,1]
    conf.eval_batch_size = {'0': 10000, '1': 10000}

    exp.data_loader = registry.sin_normal_noise()

    exp.model_factory = TfTrainEvalModelFactory(Model(name="RNADE_normal"))

    exp.hyper_param_search = GridSearch([
        Categorical([1,20,50,100,150,200], name='km'),
        Categorical([20,60,100,140,200], name='sh'),

        Categorical([128], name='bs'),
        Categorical([1], name='rs'),

        Categorical(['AdamOptimizer'], name='opt'),
        Categorical([1e-3], name='opt_lr'),
    ])

    exp.early_stopping = EarlyStop(monitor_every_epoch=1, patience=[30])

    exp.run()
