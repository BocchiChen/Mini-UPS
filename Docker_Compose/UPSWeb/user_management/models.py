from django.db import models
from django.contrib.auth.models import User

class UPSAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ups_account_number = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"""<UPSAccount object:  
                                user: {self.user.username}
                                ups account number: {self.ups_account_number}"""

    class Meta:
        db_table = "upsaccount"


TSTATUS = (
    ("idle", "idle"),
    ("traveling", "traveling"),
    ("arrive_warehouse", "arrive_warehouse"),
    ("loading", "loading"),
    ("loaded", "loaded"),
    ("delivering", "delivering")
)

class Truck(models.Model):
    truck_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=20, choices=TSTATUS)
    position_x = models.IntegerField()
    position_y = models.IntegerField()
    warehouse_id = models.IntegerField()

    def __str__(self):
        return f"""Truck object: 
                           truck_id: {self.truck_id} 
                           status: {self.status}
                           position: ({self.pos_x}, {self.pos_y})
                           warehouse id: {self.warehouse_id}"""
    class Meta:
        db_table = "trucks"

    
PSTATUS = (
    ("created", "created"),
    ("truck_en_route_to_warehouse", "truck_en_route_to_warehouse"),
    ("truck_waiting_for_package", "truck_waiting_for_package"),
    ("truck_loading", "truck_loading"),
    ("truck_loaded", "truck_loaded"),
    ("out_for_delivery", "out_for_delivery"),
    ("delivered", "delivered")
)

class Package_Info(models.Model):
    package_id = models.IntegerField(primary_key=True) # same as ship_id
    count = models.IntegerField()
    ship_id = models.IntegerField() # same as package_id
    truck = models.ForeignKey(Truck, blank=True, null=True, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=100, null=True) # aka ups_account_number
    status = models.CharField(max_length=100, choices=PSTATUS)
    destination_x = models.IntegerField(blank=True, null=True)
    destination_y = models.IntegerField(blank=True, null=True)
    warehouse_id = models.IntegerField(blank=True, null=True)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"""<Package Info:
                                  package_id: {self.package_id}
                                  count: {self.count}
                                  ship_id: {self.ship_id}
                                  truck: {self.truck.truck_id}
                                  user_id: {self.user_id}
                                  status: {self.status}
                                  destination: ({self.destination_pos_x}, {self.destination_pos_y})
                                  warehouse_id: {self.warehouse_id}
                                  description: {self.description}"""
    class Meta:
        db_table = "packages"

evcChoices = (
    ("Terrible", "Terrible"),
    ("Not great", "Not great"),
    ("Mediocre", "Mediocre"),
    ("Good", "Good"),
    ("Excellent", "Excellent"),
    ("Outstanding", "Outstanding")
)

class userEvaluation(models.Model):
    ups_number = models.CharField(max_length=100) # aka ups_account_number
    product = models.OneToOneField(Package_Info, on_delete=models.CASCADE)
    prod_quality = models.CharField(max_length=50, choices=evcChoices)
    delivery_quality = models.CharField(max_length=50, choices=evcChoices)
    description = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'evaluations'
