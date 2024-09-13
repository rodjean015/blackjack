# 1. Define a class called Animal
class Animal:
    def __init__(self, name, sound):
        # 2. Attributes (encapsulation) - name and sound
        self.name = name
        self._sound = sound  # _sound is protected (conventionally)

    # 3. Method to describe the animal
    def describe(self):
        print(f"This is a {self.name} and it says {self._sound}.")

    # 4. Method to access the sound
    def make_sound(self):
        print(f"{self.name} makes a {self._sound} sound.")

# 5. Inheritance: Define a subclass called Dog that inherits from Animal
class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name, "woof")  # Inherit properties and behaviors from Animal
        self.breed = breed  # New attribute for Dog

    # 6. Polymorphism: Override the describe method
    def describe(self):
        print(f"This is a {self.breed} dog named {self.name}. It says {self._sound}.")

# 7. Another subclass: Cat, also inherits from Animal
class Cat(Animal):
    def __init__(self, name, color):
        super().__init__(name, "meow")  # Inherit from Animal
        self.color = color  # New attribute for Cat

    # Polymorphism: Override the describe method
    def describe(self):
        print(f"This is a {self.color} cat named {self.name}. It says {self._sound}.")

# 8. Create objects (instances) of Dog and Cat
dog = Dog(name="Rex", breed="Golden Retriever")
cat = Cat(name="Whiskers", color="white")

# 9. Use methods
dog.describe()       # Outputs: This is a Golden Retriever dog named Rex. It says woof.
dog.make_sound()     # Outputs: Rex makes a woof sound.

cat.describe()       # Outputs: This is a white cat named Whiskers. It says meow.
cat.make_sound()     # Outputs: Whiskers makes a meow sound.
