import time

from .utils import meters


class ModelMeters:
    def __init__(self, metrics):
        self.batch_time_meter = meters.AverageMeter('Time')
        self.data_time_meter = meters.AverageMeter('Data')
        self.loss_meter = meters.AverageMeter('Loss')
        self.metric_meters = metrics.create_average_meters()

    def reset(self):
        self.batch_time_meter.reset()
        self.data_time_meter.reset()
        self.loss_meter.reset()
        self.metric_meters.reset()
    
    def update(
            self, metric_bundle, batch_time=None, data_time=None, loss=None,
            batch_size=1
        ):
        self.batch_time_meter.update(batch_time)
        self.data_time_meter.update(data_time)
        self.loss_meter.update(loss.item(), batch_size)
        self.metric_meters.update(metric_bundle)

    def __str__(self):
        string = (
            f'{self.batch_time_meter}\t{self.data_time_meter}'
            f'\t{self.loss_meter}\t{self.metric_meters}'
        )
        return string


class Runner:
    tags = {True: 'Training', False: 'Validation'}

    def __init__(
            self, job_name, model, loss, metrics, device,
            optimizer, scheduler, train_loader, val_loader
        ):
        super().__init__()
        self.job_name = job_name
        self.epoch = -1
        self.model = model
        self.loss = loss
        self.metrics = metrics
        self.device = device
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.loaders = {True: train_loader, False: val_loader}

        self.training = True
        self.meters = ModelMeters(metrics)

    def run_epoch(self, epoch):
        self.epoch = epoch
        self._epoch_step()
        self.meters.reset()
        start_time = time.time()
        loader = self.loaders[self.training]
        for i, inputs in enumerate(loader):
            self._iterate(i, inputs, len(loader), start_time)
            start_time = time.time()
        return self.meters.metric_meters

    def _iterate(self, i, inputs, loader_length, start_time):
        data_time = time.time() - start_time
        inputs, targets = self._parse_data(inputs)
        loss, metric_bundle = self._forward(inputs, targets)
        self._step(loss)
        batch_time = time.time() - start_time
        self.meters.update(
            metric_bundle, batch_time, data_time, loss,
            batch_size=inputs.size(0)
        )
        self.print_stats(i + 1, loader_length)
        start_time = time.time()

    def train(self, training):
        self.training = training
        self.model.train(self.training)

    def _epoch_step(self):
        pass

    def print_stats(self, iteration, total_iterations):
        print(f'{self._get_header(iteration, total_iterations)}\t{self.meters}')

    def _get_header(self, iteration, total_iterations):
        header = (
            f'{self.tags[self.training]} epoch {self.epoch}:'
            f' {iteration}/{total_iterations}'
        )
        return header

    def _parse_data(self, inputs):
        image, label = inputs
        image = image.to(self.device)
        label = label.to(self.device)
        return image, label

    def _forward(self, inputs, targets):
        outputs = self.model(inputs)
        loss = self.loss(outputs, targets)
        metric_bundle = self.metrics(outputs, targets)
        return loss, metric_bundle

    def _step(self, loss):
        if self.training:
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            self.scheduler.step()
