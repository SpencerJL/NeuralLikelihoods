from skopt.space import Categorical

from conf import conf
from data import registry
from experiment.early_stop import EarlyStop
from experiment.experiment import Experiment
from experiment.hyper_param_opt import GridSearch
from models.tensorflow.model import Model
from models.tensorflow.tf_train_eval import TfTrainEvalModelFactory

if __name__ == '__main__':
    exp = Experiment('density/synthetic/mv_nonlinear')

    conf.num_workers = 4
    conf.visible_device_list = [0,1]
    conf.eval_batch_size = {'0': 10000, '1': 10000}

    exp.data_loader = registry.mv_nonlinear()

    exp.model_factory = TfTrainEvalModelFactory(Model(name="MONDE_copula_const_cov"))

    exp.hyper_param_search = GridSearch([
        Categorical([32, 64,128], name='hxy_sh'),
        Categorical([1,2,3], name='hxy_nh'),

        Categorical([32, 64, 128], name='x_sh'),
        Categorical([2,3,4], name='x_nh'),

        Categorical([16,32], name='hxy_x'),

        Categorical([0.05, 0.01], name='clr'),

        Categorical([128], name='bs'),
        Categorical([1], name='rs'),

        Categorical(['AdamOptimizer'], name='opt'),
        Categorical([1e-4,1e-3,1e-2], name='opt_lr'),
    ])

    exp.early_stopping = EarlyStop(monitor_every_epoch=1, patience=[30])

    exp.run()