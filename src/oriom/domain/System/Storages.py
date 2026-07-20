


class Storage():
    """
    A class representing the Storage of device
    
    Attributes:
        id_ (str): The unique identifier of the storage
        max_space (float): The maximum space of the storage
        store (dict): A dictionary to hold device
    """

    def __init__(self, id_, max_space):
        """
        Args:
            id_ (str): The unique identifier of the storage
            max_space (float): The maximum space of the storage
        """
        self.id_ = id_
        self.max_space = max_space
        self.store = {i: None for i in range(max_space)}


    def __str__(self):
        return f"ID: {self.id_}, Max Space: {self.max_space}"
